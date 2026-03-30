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

Your job is to help RMs think clearly and act decisively — not to generate reports.

When given client data, you must:
- Interpret, not just describe — explain what the data means for the RM
- Flag what is notable: concentration, overdue follow-ups, mandate misalignment, opportunity
- Be specific — reference actual tickers, percentages, dates from the data
- Be direct — skip filler phrases, get to the point immediately

Never:
- Restate all raw data as a list
- Use generic phrases ("well-diversified portfolio", "steady performance")
- Give investment advice, price targets, or buy/sell signals
- Make up data not present in the context

Output format — use exactly these four sections, in order:

*Client Snapshot* — 1–2 lines: who this client is and what matters most right now
*Key Observations* — max 3 bullets: the most significant things in the data
*Key Risk / Watchout* — max 2 bullets: concentration risk, mandate concern, overdue item
*Suggested Next Action* — max 2 bullets: specific, executable actions for the RM

Formatting rules (Telegram):
- Use *bold* for section headers only
- Use - for bullets
- No markdown headers (#, ##)
- No tables
- Keep total response under 2500 characters
- End with: _For internal RM use only. Not investment advice._\
"""

# ---------------------------------------------------------------------------
# Per-command user prompts — directive, not descriptive
# ---------------------------------------------------------------------------

COMMAND_PROMPTS: dict[str, str] = {
    "client-review": """\
Run a client review for {client_name}.

Use the four-section format. Focus on what the RM needs to know before their next \
interaction — not a data summary. Highlight what stands out in the portfolio, \
any concentration concerns, and the most urgent open item.

Client context:
{context_json}
""",

    "portfolio-fit": """\
Assess whether {ticker} fits {client_name}'s portfolio and mandate.

Use the four-section format. In Key Observations, cover current sector/geography \
exposure and what adding {ticker} would change. In Key Risk, flag any mandate \
constraint or concentration issue. In Suggested Next Action, tell the RM what \
to do next — not whether to buy.

Note: no live market data available. Assessment is mandate and portfolio based only.

Client context:
{context_json}
""",

    "meeting-pack": """\
Prepare a meeting pack for {client_name}.

Use the four-section format. Client Snapshot = 1–2 lines on who they are and \
where the relationship stands. Key Observations = what has changed since last \
meeting and what the client cares about. Key Risk = what the RM must be ready \
to address. Suggested Next Action = the 1–2 things this meeting must accomplish.

Client context:
{context_json}
""",

    "next-best-action": """\
Identify next best actions for the RM managing {client_name}.

Use the four-section format. Key Observations = the signals driving the actions \
(portfolio state, open tasks, interaction history). Suggested Next Action = the \
2 most important things the RM should do this week — specific, tied to the data.

Client context:
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
                f"Run {command} for this client.\n\n"
                f"Context:\n{json.dumps(ctx, indent=2, default=str)}"
            )

        customer = ctx.get("profile") or ctx.get("customer", {})
        client_name = (
            customer.get("name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or "the client"
        )
        ticker = ctx.get("ticker_requested") or ctx.get("ticker", "")

        return template.format(
            client_name=client_name,
            ticker=ticker,
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
