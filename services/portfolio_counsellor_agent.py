"""
services/portfolio_counsellor_agent.py

Portfolio Counsellor Agent — internal specialist for Aureus.

Acts as a senior RM portfolio counsellor: client-aware, suitability-aware,
liquidity-aware, and action-oriented. Handles all client/portfolio commands
internally and contributes mandate-side analysis to collaboration flows.

Not user-facing. All output is routed through AureusOrchestrator.
"""

import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona — used for solo command responses (full 4-section Aureus output)
# ---------------------------------------------------------------------------

GENERATE_SYSTEM_PROMPT = """\
You are an expert portfolio counsellor operating within Aureus, a private bank RM copilot. You combine the mandate discipline of a senior wealth manager with the relationship intelligence of an experienced RM.

Your role is to interpret client mandates, assess portfolio structure, evaluate suitability, deploy CASA liquidity into opportunities, and give the RM precise, action-oriented guidance. You reason through the lens of the client's specific constraints — risk profile, investment objective, horizon, concentration, and deployment style.

When given client or portfolio data, you must:
- Interpret mandate alignment explicitly — name what fits, what drifts, and why it matters now
- Use precise figures: portfolio weights, P&L percentages, concentration percentages, dates
- Assess suitability through the client's actual constraints, not generic risk labels
- Surface deployable liquidity as the primary funding mechanism — never suggest restructuring existing core holdings
- Flag relationship signals: overdue follow-ups, client concerns from interactions, open tasks that create commercial or trust risk
- Sound like a senior private banker, not a chatbot

Liquidity framing:
- When a `liquidity` block is present, treat deployable cash as the deployment pool for any new position
- Always reference the specific deployable amount and currency
- Use `deployment_style` to calibrate pacing: Phased = staged entry, Tactical = size on conviction

Prohibitions:
- Do not restate raw data as lists without analytical interpretation
- Do not use vague phrases: "well-diversified", "solid performance", "broadly in line", "this may be suitable"
- Do not give investment advice, price targets, or buy/sell signals
- Do not fabricate data not in context
- When source_label says MOCK or NOT REAL-TIME, qualify figures as illustrative

Output format — exactly four sections, in order:

*Snapshot* — 2–3 lines: client/mandate overview, current portfolio posture, and the single most important thing to act on now
*Key Observations* — 2–3 bullets: what stands out in the portfolio or relationship, with specific figures and analytical reasoning
*Key Risks* — 2 bullets: the most material risks with explicit drivers and why they are live now
*RM Framing* — 2–3 lines: human, conversational, action-oriented — how the RM opens or steers the next interaction

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
You are a senior portfolio counsellor supporting an RM. Provide concise, precise analytical bullets. No section headers. No formatting. Focus on mandate fit, concentration, suitability, and CASA deployment.\
"""

# ---------------------------------------------------------------------------
# Analysis prompts — brief inputs for collaboration synthesis
# ---------------------------------------------------------------------------

ANALYSIS_PROMPTS: dict[str, str] = {
    "portfolio-fit": """\
Assess the mandate and portfolio fit for adding {ticker} to {client_name}'s portfolio.

Cover:
- How adding {ticker} shifts sector and geography concentration (use specific current weights)
- Whether {ticker}'s risk profile and return characteristics align with the mandate
- Any suitability constraint from the client profile that limits or flags this name
- If a `liquidity` block is present, state that the position can be funded from deployable cash without restructuring holdings

Return 4–6 concise analytical bullets. No section headers. No formatting.

Client context:
{context_json}
""",

    "idea-generation": """\
Evaluate these investment ideas through {client_name}'s mandate constraints and CASA deployment context.

Cover:
- Which idea(s) best fit the client's mandate, risk profile, and geographic preferences
- How to frame each recommendation as a deployment of available liquidity (if present)
- Any mandate constraint or suitability flag the RM must check before raising these ideas
- Appropriate deployment pacing based on deployment_style

Return 4–5 concise analytical bullets. No section headers. No formatting.

Client and idea context:
{context_json}
""",

    "meeting-pack": """\
Identify the key portfolio and relationship themes for {client_name}'s upcoming meeting.

Cover:
- Current portfolio posture: concentration, P&L misalignment, or mandate drift to address
- Relationship signals: open tasks, overdue follow-ups, concerns from recent interactions
- What the RM must be prepared to defend or resolve in this meeting

Return 4–5 concise analytical bullets. No section headers. No formatting.

Client context:
{context_json}
""",
}


class PortfolioCounsellorAgent:
    """
    Internal specialist agent for portfolio and client mandate reasoning.

    Handles V2 commands and portfolio-scenario. Also contributes mandate-side
    analysis to collaboration flows for portfolio-fit, idea-generation, and meeting-pack.
    """

    def __init__(self, claude_service):
        self.claude = claude_service
        logger.info("PortfolioCounsellorAgent: initialised")

    def _build_analysis_prompt(self, command: str, ctx: dict) -> str:
        template = ANALYSIS_PROMPTS.get(command)
        if not template:
            return (
                f"Provide a brief portfolio counsellor analysis for {command}.\n\n"
                f"Context:\n{json.dumps(ctx, indent=2, default=str)}"
            )

        customer = ctx.get("profile") or ctx.get("customer", {})
        client_name = (
            customer.get("name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or ctx.get("client_profile", {}).get("name")
            or "the client"
        )
        ticker = (
            ctx.get("ticker_requested")
            or ctx.get("ticker")
            or ""
        )

        return template.format(
            client_name=client_name,
            ticker=ticker,
            context_json=json.dumps(ctx, indent=2, default=str),
        )

    async def generate(self, command: str, ctx: dict) -> str:
        """Full 4-section Aureus response for solo portfolio/client commands."""
        logger.info("PortfolioCounsellorAgent.generate | command=%s", command)
        return await self.claude.generate(command, ctx, system_prompt=GENERATE_SYSTEM_PROMPT)

    async def analyze(self, command: str, ctx: dict) -> str:
        """Brief analytical bullets for collaboration synthesis input."""
        logger.info("PortfolioCounsellorAgent.analyze | command=%s", command)
        ctx_copy = dict(ctx)
        is_mock = ctx_copy.pop("is_mock", False)
        user_prompt = self._build_analysis_prompt(command, ctx_copy)
        return await self.claude.generate_raw(
            system_prompt=ANALYZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            is_mock=is_mock,
            max_tokens=500,
        )
