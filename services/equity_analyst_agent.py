"""
services/equity_analyst_agent.py

Equity Analyst Agent — internal specialist for Aureus.

Acts as an embedded institutional equity analyst: thesis-aware, catalyst-driven,
precise, and slightly verbose where research depth is warranted. Handles all
equity research commands internally and contributes stock-side analysis to
collaboration flows.

Not user-facing. All output is routed through AureusOrchestrator.
"""

import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona — used for solo command responses (full 4-section Aureus output)
# ---------------------------------------------------------------------------

GENERATE_SYSTEM_PROMPT = """\
You are an institutional equity analyst operating within Aureus, a private bank RM copilot. You combine the rigor of a sell-side research analyst with the RM-usability of an embedded desk analyst.

Your role is to interpret earnings results, identify catalysts, validate investment theses, generate mandate-aligned ideas, and deliver RM-ready stock intelligence. You explain what changed, why it matters, and what the RM should do with it. Slight verbosity is appropriate when explaining thesis drivers or risk mechanisms — precision matters more than brevity for research content.

When given stock or market data, you must:
- Interpret earnings beats/misses by quality, not just headline number — revenue vs. cost-driven, guidance credibility, margin trajectory
- Identify catalysts with explicit timing and mechanism — not just labels, but what happens and why it moves the stock
- Validate or challenge a thesis by naming the conditions required for it to play out
- Generate ideas that are specific to the client mandate — sector fit, geography, conviction level, CASA deployment
- Surface what would cause the thesis to break — be precise about triggers and timing
- Sound like an analyst briefing an RM, not a summary generator

Prohibitions:
- Do not restate raw data as lists without interpretation
- Do not use vague phrases: "solid results", "notable headwinds", "broadly in line", "potential upside"
- Do not give buy/sell signals or price targets
- Do not fabricate data not in context
- When source_label says MOCK or NOT REAL-TIME, qualify figures as illustrative

Output format — exactly four sections, in order:

*Snapshot* — 2–3 lines: company/ticker overview, current conviction or narrative context, and the single most important thing for the RM to know right now
*Key Observations* — 2–3 bullets: the analytical substance — what changed, why it matters, specific figures, thesis implications
*Key Risks* — 2 bullets: the most material risks with explicit drivers and timing — what event or data point would cause this to disappoint
*RM Framing* — 2–3 lines: how the RM uses this intelligence in a client conversation — purposeful and direct

Formatting rules (Telegram):
- *bold* for section headers only
- - for bullets
- No markdown headers, no tables, no nested bullets
- Keep total response under 3200 characters
- End with: _For internal RM use only. Not investment advice._\
"""

# ---------------------------------------------------------------------------
# Persona — used for brief analysis in collaboration flows
# ---------------------------------------------------------------------------

ANALYZE_SYSTEM_PROMPT = """\
You are an institutional equity analyst supporting an RM. Provide concise, precise analytical bullets covering thesis quality, catalysts, and key risks. No section headers. No formatting.\
"""

# ---------------------------------------------------------------------------
# Analysis prompts — brief inputs for collaboration synthesis
# ---------------------------------------------------------------------------

ANALYSIS_PROMPTS: dict[str, str] = {
    "portfolio-fit": """\
Assess the investment case for {ticker} as a potential addition to a client's portfolio.

Cover:
- Core thesis: what drives the bull case, what is the bear case sensitive to right now
- Near-term catalysts: what are they, when expected, why they matter
- Key risks: 2 most material risks that could undermine the thesis near-term
- Conviction level and whether the current setup is compelling

Return 4–6 concise analytical bullets. No section headers. No formatting.

Stock context:
{context_json}
""",

    "idea-generation": """\
Evaluate the thesis quality and conviction strength of these investment ideas.

Cover:
- For each idea: thesis integrity (is the bull case credible now?), key catalyst timing, and the most material risk
- Which idea has the strongest near-term setup given the current narrative
- Any factor that would make the RM hesitate to raise this name with clients now

Return 4–6 concise analytical bullets. No section headers. No formatting.

Ideas context:
{context_json}
""",

    "meeting-pack": """\
For each stock in this client's portfolio, provide a brief current story.

Cover:
- Thesis status: intact, under pressure, or improved since last review
- Any recent catalyst, earnings update, or narrative shift the RM must know
- One thing the RM should be ready to discuss per key holding

Return 1–2 lines per holding as concise bullets. No section headers. No formatting.

Stock context:
{context_json}
""",
}


class EquityAnalystAgent:
    """
    Internal specialist agent for equity research and stock-level reasoning.

    Handles V3 equity research commands and contributes thesis/catalyst
    analysis to collaboration flows for portfolio-fit, idea-generation, and meeting-pack.
    """

    def __init__(self, claude_service):
        self.claude = claude_service
        logger.info("EquityAnalystAgent: initialised")

    def _build_analysis_prompt(self, command: str, ctx: dict) -> str:
        template = ANALYSIS_PROMPTS.get(command)
        if not template:
            return (
                f"Provide a brief equity analyst assessment for {command}.\n\n"
                f"Context:\n{json.dumps(ctx, indent=2, default=str)}"
            )

        ticker = (
            ctx.get("ticker_requested")
            or ctx.get("ticker")
            or ""
        )

        return template.format(
            ticker=ticker,
            context_json=json.dumps(ctx, indent=2, default=str),
        )

    async def generate(self, command: str, ctx: dict) -> str:
        """Full 4-section Aureus response for solo equity research commands."""
        logger.info("EquityAnalystAgent.generate | command=%s", command)
        return await self.claude.generate(command, ctx, system_prompt=GENERATE_SYSTEM_PROMPT)

    async def analyze(self, command: str, ctx: dict) -> str:
        """Brief analytical bullets for collaboration synthesis input."""
        logger.info("EquityAnalystAgent.analyze | command=%s", command)
        ctx_copy = dict(ctx)
        is_mock = ctx_copy.pop("is_mock", False)
        user_prompt = self._build_analysis_prompt(command, ctx_copy)
        return await self.claude.generate_raw(
            system_prompt=ANALYZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            is_mock=is_mock,
            max_tokens=500,
        )
