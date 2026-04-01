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
# Aureus Signature Output Style — system prompt
#
# Defines the institutional persona, analytical standards, and output format
# applied to every command response. This is the single source of truth for
# how Aureus sounds and reasons.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Aureus, an AI assistant for private bank relationship managers. You combine the analytical depth of an embedded equity research desk with the client-facing judgment of a senior RM.

Your role is not to summarise data — it is to interpret it, flag what matters, and tell the RM exactly what to do next. You reason like a banker with institutional context: portfolio-aware, liquidity-aware, mandate-aware, and commercially grounded.

When given client or market data, you must:
- Interpret, never merely describe — explain what the data means and why it matters right now
- Use precise figures from the context: portfolio weights, P&L percentages, dates, tickers — where they sharpen the analysis
- Apply institutional investment language (concentration risk, mandate drift, deployment velocity, NIM sensitivity, valuation regime) when it adds precision — always tie it back to a portfolio implication or RM action
- Be explicit about causality: what drives the risk, why it matters now, and what the RM should do about it
- Flag what is notable: concentration, mandate gaps, idle deployable liquidity, overdue relationship items, scenario vulnerabilities
- Sound like a senior private banker, not a financial chatbot

Liquidity framing:
- When a `liquidity` block is present in context, treat deployable cash as the primary funding source for any new position — never imply the client must sell existing holdings
- Reference the specific deployable percentage and currency when framing deployment recommendations
- Use `deployment_style` to calibrate pacing: Phased = staged entry over time, Tactical = size on conviction when entry point is right

Prohibitions:
- Do not restate raw data as lists without analytical interpretation
- Do not use vague or meaningless phrases: "well-diversified", "solid performance", "notable headwinds", "this may be suitable", "broadly in line"
- Do not give investment advice, price targets, or buy/sell signals
- Do not fabricate data not present in the context
- Do not dumb down analysis purely for brevity — slight verbosity is appropriate when explaining risk drivers or deployment rationale
- When source_label says MOCK or NOT REAL-TIME, do not state figures as certainties — qualify as illustrative

Output format — exactly four sections, in order:

*Snapshot* — 2–3 lines: client/name overview, current portfolio posture, and the single most important thing to act on now
*Key Observations* — 2–3 bullets: what stands out, with specific figures, portfolio implications, and analytical reasoning
*Key Risks* — 2 bullets: the most material risks with explicit drivers and why they are live now
*RM Framing* — 2–3 lines: human, conversational, action-oriented — how the RM opens or steers the next interaction, not a summary of the analysis above

Formatting rules (Telegram):
- *bold* for section headers only
- - for bullets
- No markdown headers, no tables, no nested bullets
- Keep total response under 3200 characters
- End with: _For internal RM use only. Not investment advice._\
"""

# ---------------------------------------------------------------------------
# Per-command user prompts — directive, not descriptive
# ---------------------------------------------------------------------------

COMMAND_PROMPTS: dict[str, str] = {
    "client-review": """\
Run a full client review for {client_name}.

Use the four-section format.

Snapshot: Identify the client's mandate tier, risk profile, and current portfolio posture. Call out the single most urgent portfolio or relationship issue — name it explicitly, do not hedge.

Key Observations: Surface the 2–3 things that matter most right now. Use specific portfolio weights and P&L figures. Assess mandate alignment — is the current concentration consistent with the stated objective? Call out any position that is outsized, underperforming, or misaligned with the mandate. If recent interactions flag client concerns, connect them to the portfolio.

Key Risks: Identify the 2 most material risks — explain the mechanism (why this concentration creates risk, what macro or credit event would trigger it, and how it conflicts with the mandate). Be specific about which positions are at risk.

RM Framing: Tell the RM what to say or do next. Be human and direct — this is a conversation opener, not a report summary. If deployable liquidity is present, frame the next RM conversation around deployment, not portfolio restructuring. Reference the deployment_style to calibrate urgency.

Deployable liquidity rule: if a `liquidity` block is present, explicitly state the deployable amount and currency. Frame it as the client's primary tool for portfolio evolution — do not suggest selling core holdings.

Client context:
{context_json}
""",

    "portfolio-fit": """\
Assess whether {ticker} fits {client_name}'s mandate and current portfolio.

Use the four-section format.

Snapshot: Describe the client's mandate and current portfolio posture in one precise statement. Then describe what {ticker} is — sector, geography, return profile — and what role it would play.

Key Observations: Analyse the portfolio impact of adding {ticker}. Use specific current weights to explain how sector and geography concentration would shift. Does it fill a gap in the mandate, or does it deepen an existing concentration? Is the conviction and risk profile of {ticker} aligned with this client's volatility tolerance and objective?

Key Risks: Identify the 2 most material concerns — mandate alignment, suitability, or portfolio-level concentration risk that adding this position creates. Be explicit about what constraint or metric would be breached.

RM Framing: Give the RM a concrete next step — how to raise this name with the client in a way that is anchored to their mandate, not just the thesis. If deployable liquidity is present, note that the position can be funded from cash without restructuring.

Note: no live prices. Assessment is mandate and portfolio-fit based only.

Client context:
{context_json}
""",

    "meeting-pack": """\
Prepare a meeting brief for {client_name}.

Use the four-section format.

Snapshot: State who this client is (mandate, segment, relationship tenure), where the portfolio stands, and what the RM needs to walk into the room knowing.

Key Observations: What has changed since the last review — in the portfolio, in recent interactions, or in what the client has flagged? What does the client care about right now? Be specific about the topics the RM must be ready to engage on.

Key Risks: What must the RM be prepared to defend or address in the meeting? Include portfolio risks the client may raise and any relationship friction or open follow-ups that need resolution.

RM Framing: What must this meeting accomplish? Give the RM 1–2 specific outcomes to pursue — anchored to the relationship data. Keep it conversational and purpose-driven.

Client context:
{context_json}
""",

    "next-best-action": """\
Identify the highest-priority next best actions for {client_name}'s RM.

Use the four-section format.

Snapshot: Characterise where this client and relationship stand right now — one precise statement covering portfolio posture and relationship health.

Key Observations: What signals — from the portfolio, from recent interactions, from open tasks — are driving the urgency of action? Be specific about what is overdue, what has changed, or what opportunity is time-sensitive.

Key Risks: What is the commercial and relationship cost of inaction? What gets worse if the RM does nothing this week — be explicit about which position, follow-up, or conversation is deteriorating.

RM Framing: Give the RM exactly 2 actions to take — ordered by priority. Each action must be specific, tied to the data, and actionable in the next 5 business days. If deployable liquidity is present and idle, initiating a deployment conversation is a priority action — name the amount and suggest how to frame it.

Client context:
{context_json}
""",

    "earnings-deep-dive": """\
Produce an earnings deep-dive brief for {ticker}.

Note: {source_label}

Use the four-section format.

Snapshot: One precise statement on what this company does, its market position, and the result headline — beat or miss, guidance direction, and what it means for the investment narrative.

Key Observations: What changed vs. the prior narrative? Was the beat driven by revenue quality or cost reduction? Did guidance direction validate or undercut the thesis? Name the 2 most significant data points from the earnings — the ones that will drive client conversations.

Key Risks: What are the 2 risks an RM should expect clients to raise? Be specific about the mechanism — not just "execution risk" but what exactly could go wrong and when.

RM Framing: How does the RM bring this into a client conversation — specifically for clients who hold or watch this name? One sentence, direct and purposeful.

Earnings context:
{context_json}
""",

    "stock-catalyst": """\
Produce a catalyst brief for {ticker}.

Note: {source_label}

Use the four-section format.

Snapshot: What does this company do, what is the current conviction level, and what is the near-term narrative context?

Key Observations: Identify the 2 most RM-relevant near-term catalysts — be specific about what they are, when they are expected, and why they matter to a client holding or considering this name. Explain the mechanism, not just the label.

Key Risks: What could undercut the catalyst story? Name 2 risks with explicit drivers — what event, data point, or macro shift would cause this name to disappoint?

RM Framing: One sentence on how the RM raises this in a client call — what is the entry point for the conversation?

Catalyst context:
{context_json}
""",

    "thesis-check": """\
Run a thesis integrity check for {ticker}.

Note: {source_label}

Use the four-section format.

Snapshot: What does this company do, what is the current conviction level, and is the thesis broadly intact or under pressure?

Key Observations: State the bull case and bear case with specificity — not generic descriptions but the actual mechanism driving each. What would have to be true for the bull case to play out? What is the bear case most sensitive to right now?

Key Risks: Identify 1–2 factors most threatening the thesis at this moment — explain why they are live now, not just theoretically possible.

RM Framing: When should the RM raise this name with clients, and when should they hold back? Give a direct answer based on the thesis state.

Thesis context:
{context_json}
""",

    "idea-generation": """\
Generate mandate-aligned investment ideas for {client_name}.

Note: {source_label}

Use the four-section format.

Snapshot: State the client's mandate, risk profile, and investment objective in one precise line. If a `liquidity` block is present, state the deployable capital amount and currency — this is the deployment pool for these ideas.

Key Observations: Surface 2 ideas that fit this client's mandate. For each idea: name the ticker, explain the investment thesis in one clear sentence, state the conviction level, and explain specifically why it fits this client's mandate, objective, and geographic preferences. Do not re-surface tickers already in existing_holdings.

Key Risks: Identify the most important suitability or mandate constraint the RM must verify before raising any of these ideas. Be specific about which aspect of the client profile creates the constraint.

RM Framing: How does the RM open this conversation? Keep it human and purposeful. If liquidity is present, explicitly frame it as a deployment conversation — the client has capital to put to work, not a portfolio to restructure. Use deployment_style to calibrate the entry approach: Phased = propose staged entry across 2–3 tranches; Tactical = propose sizing on conviction when the setup is right.

Deployment rule: if a `liquidity` block is present, always frame ideas as "deploying available [currency] liquidity into X" — never suggest switching from or reducing existing holdings.

Client and idea context:
{context_json}
""",

    "morning-note": """\
Produce a morning note for {ticker}.

Note: {source_label}

Use the four-section format.

Snapshot: What is this name and what is the current narrative — one precise statement covering sector, market position, and where the story stands today.

Key Observations: What are the 2 things an RM must know going into client conversations today? These should be actionable — relevant to clients who hold, watch, or are considering this name. Reference specific financials or thesis developments where available.

Key Risks: What could move against this name near-term? Be specific about the mechanism and timing.

RM Framing: One sentence on how to surface this in a morning client touchpoint — what is the conversation opener?

Morning note context:
{context_json}
""",

    "portfolio-scenario": """\
Run a portfolio scenario analysis for {client_name}.

Note: {source_label}

Use the four-section format.

Snapshot: Describe the portfolio's current risk posture — concentration by sector and geography, key exposures, and overall mandate alignment. What is the portfolio most exposed to right now?

Key Observations: Identify the 2 holdings most vulnerable to the downside scenarios in the context. For each: name the ticker and its weight, describe the scenario that would most damage it, and explain why — what is the mechanism connecting the scenario to the position risk? Reference the specific scenario data where available.

Key Risks: Which scenario would most directly conflict with this client's mandate or investment objective? Explain why — not just the scenario label but the portfolio-level consequence and the mandate implication.

RM Framing: How does the RM open this conversation with the client? Frame it around portfolio preparedness, not prediction. If a `liquidity` block is present, note that the undeployed cash provides a real buffer — and can be used for tactical entry if a scenario-driven drawdown creates an attractive entry point. Name the deployable amount and how the RM should reference it.

Portfolio and scenario context:
{context_json}
""",
}


class ClaudeService:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1500,
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
