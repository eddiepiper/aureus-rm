"""
services/claude_service.py

Claude API wrapper for Aureus RM Copilot.

Builds concise, insight-focused prompts from compressed client context
and calls Claude to generate RM-quality responses.
"""

import json
import logging
from typing import Optional

import anthropic
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — defines Aureus persona and strict output format
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Aureus, an AI copilot for private bank relationship managers.

Your job is to help RMs think clearly and act decisively — not to produce reports.

When given data, you must:
- Interpret, not just describe — say what it means for the RM
- Flag what is notable: concentration, overdue items, mandate gaps, opportunity
- Be specific — reference tickers, dates, and key facts from the context
- Be direct — no filler, no preamble, get to the point immediately

Never:
- Restate raw data as a list
- Use vague phrases ("well-diversified", "solid performance", "notable headwinds")
- Give investment advice, price targets, or buy/sell signals
- Make up data not present in the context
- Use hedge-heavy analyst language ("materially", "meaningfully", "significantly")
- State precise figures as certainties when data is framework-based

Output format — exactly four sections, in order:

*Snapshot* — 1–2 lines max
*Key Observations* — max 2 bullets
*Key Risks* — max 2 bullets
*RM Framing* — 1–2 lines: what the RM says or does next

Formatting rules (Telegram):
- *bold* for section headers only
- - for bullets
- No markdown headers, no tables
- Keep total response under 2000 characters
- End with: _For internal RM use only. Not investment advice._\
"""

# ---------------------------------------------------------------------------
# Per-command user prompts — directive, not descriptive
# ---------------------------------------------------------------------------

COMMAND_PROMPTS: dict[str, str] = {
    "client-review": """\
Client review for {client_name}.

Use the four-section format.
Snapshot = who this client is and what needs attention right now.
Key Observations = 2 things that stand out in the portfolio or relationship.
Key Risks = the most pressing concentration or mandate concern.
RM Framing = the one action the RM should take before the next interaction.

Client context:
{context_json}
""",

    "portfolio-fit": """\
Does {ticker} fit {client_name}'s portfolio?

Use the four-section format.
Snapshot = client mandate in one line.
Key Observations = how {ticker} changes current sector or geography exposure.
Key Risks = any mandate constraint or concentration issue adding {ticker} would create.
RM Framing = what the RM should do next — not whether to buy.

Note: no live prices. Assessment is mandate and portfolio based only.

Client context:
{context_json}
""",

    "meeting-pack": """\
Meeting prep for {client_name}.

Use the four-section format.
Snapshot = who they are and where the relationship stands.
Key Observations = what has changed since last meeting and what the client cares about.
Key Risks = what the RM must be ready to address in the room.
RM Framing = the 1–2 things this meeting must accomplish.

Client context:
{context_json}
""",

    "next-best-action": """\
Next best actions for {client_name}'s RM.

Use the four-section format.
Snapshot = one line on where this client and relationship stand.
Key Observations = the signals driving the recommended actions.
Key Risks = what happens if the RM does nothing this week.
RM Framing = the 2 most important actions to take — specific and tied to the data.

Client context:
{context_json}
""",

    "earnings-deep-dive": """\
Earnings brief for {ticker}.

Note: {source_label}

Use the four-section format.
Snapshot = what this company does, one line.
Key Observations = beat or miss, guidance direction, and what changed vs. prior narrative.
Key Risks = 2 risks the RM should expect clients to raise.
RM Framing = one sentence on how to bring this up with a client who holds or watches this name.

Earnings context:
{context_json}
""",

    "stock-catalyst": """\
Catalyst brief for {ticker}.

Note: {source_label}

Use the four-section format.
Snapshot = what the company does and current conviction.
Key Observations = the 2 near-term catalysts most relevant to an RM conversation.
Key Risks = 2 risks that could undercut the catalyst story.
RM Framing = one sentence on how to raise this in a client call.

Catalyst context:
{context_json}
""",

    "thesis-check": """\
Thesis check for {ticker}.

Note: {source_label}

Use the four-section format.
Snapshot = what the company does and conviction level, one line.
Key Observations = the bull case and bear case, one sentence each.
Key Risks = 1–2 factors that most threaten the thesis now.
RM Framing = when to raise this name and when to hold back.

Thesis context:
{context_json}
""",

    "idea-generation": """\
Stock ideas for {client_name}.

Note: {source_label}

Use the four-section format.
Snapshot = client mandate in one line.
Key Observations = 2 ideas that fit this client's profile, with a one-line rationale each.
Key Risks = the most important suitability concern to check before raising any idea.
RM Framing = how to open the conversation — one sentence.

Note: if existing_holdings are listed, do not re-surface those names as new ideas.

Client and idea context:
{context_json}
""",

    "morning-note": """\
Morning note for {ticker}.

Note: {source_label}

Use the four-section format.
Snapshot = what this name is and one line on the current narrative.
Key Observations = 2 things the RM should know going into client conversations today.
Key Risks = what could move against this name near-term.
RM Framing = one sentence on how to surface this in a morning touchpoint.

Morning note context:
{context_json}
""",

    "portfolio-scenario": """\
Portfolio scenario check for {client_name}.

Note: {source_label}

Use the four-section format.
Snapshot = portfolio posture in one line.
Key Observations = the 2 holdings most exposed to downside scenarios and why.
Key Risks = the scenario that would most conflict with this client's mandate.
RM Framing = how to open this conversation — frame it as preparedness, not prediction.

Portfolio and scenario context:
{context_json}
""",
}


class ClaudeService:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
    ):
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def _build_user_prompt(self, command: str, ctx: dict) -> str:
        template = COMMAND_PROMPTS.get(command)
        if not template:
            return (
                f"Run {command} for this context.\n\n"
                f"Context:\n{json.dumps(ctx, indent=2, default=str)}"
            )

        # Client name — works for compressed ('profile' key) and raw ('customer' key) shapes
        customer = ctx.get("profile") or ctx.get("customer", {})
        client_name = (
            customer.get("name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or ctx.get("client_profile", {}).get("name")
            or "the client"
        )

        # Ticker — direct key
        ticker = (
            ctx.get("ticker_requested")
            or ctx.get("ticker")
            or ctx.get("ticker_a", "")
            or ""
        )

        # source_label for mock data banner in prompt
        source_label = ctx.get("source_label", "MOCK / NOT REAL-TIME")

        return template.format(
            client_name=client_name,
            ticker=ticker,
            source_label=source_label,
            context_json=json.dumps(ctx, indent=2, default=str),
        )

    async def generate(self, command: str, ctx: dict) -> str:
        """
        Async: call Claude and return a Telegram-ready response string.
        ctx should already be compressed by command_router._compress_context().
        """
        is_mock = ctx.pop("is_mock", False)
        mock_banner = "⚠️ *MOCK DATA* — illustrative only\n\n" if is_mock else ""

        user_prompt = self._build_user_prompt(command, ctx)

        logger.info("Claude API call | command=%s | model=%s", command, self.model)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = message.content[0].text
            logger.info(
                "Claude response | in=%d out=%d tokens",
                message.usage.input_tokens,
                message.usage.output_tokens,
            )
            return mock_banner + text

        except anthropic.AuthenticationError:
            logger.error("Claude auth failed — check ANTHROPIC_API_KEY")
            raise
        except anthropic.RateLimitError:
            logger.warning("Claude rate limit hit")
            raise
        except Exception as e:
            logger.exception("Claude API error: %s", e)
            raise
