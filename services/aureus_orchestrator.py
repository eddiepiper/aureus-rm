"""
services/aureus_orchestrator.py

Aureus Orchestrator — internal routing and synthesis layer.

Receives generation requests from CommandRouter (same interface as ClaudeService),
routes work to the appropriate internal specialist agent, and synthesises outputs
into a single unified Aureus response.

Architecture:
  CommandRouter → AureusOrchestrator → PortfolioCounsellorAgent
                                     → EquityAnalystAgent
                                     → synthesis (Claude) → unified response

The user never interacts with agents directly. Aureus is the only visible layer.
"""

import asyncio
import json
import logging

from services.claude_service import SYSTEM_PROMPT as AUREUS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Command ownership — primary agent per command
# ---------------------------------------------------------------------------

# Commands handled solely by the Portfolio Counsellor Agent
_PORTFOLIO_COMMANDS = frozenset({
    "client-review",
    "next-best-action",
    "portfolio-scenario",
})

# Commands handled solely by the Equity Analyst Agent
_EQUITY_COMMANDS = frozenset({
    "earnings-deep-dive",
    "stock-catalyst",
    "thesis-check",
    "morning-note",
})

# Commands requiring collaboration between both agents
_COLLABORATION_COMMANDS = frozenset({
    "portfolio-fit",
    "idea-generation",
    "meeting-pack",
})

# ---------------------------------------------------------------------------
# Synthesis prompts — per collaboration command
# ---------------------------------------------------------------------------

_SYNTHESIS_PROMPTS: dict[str, str] = {
    "portfolio-fit": """\
You have received specialist analyses for a portfolio fit assessment.

Portfolio Counsellor Analysis (mandate fit, concentration, suitability, CASA):
{portfolio_analysis}

Equity Analyst Analysis (thesis, catalysts, risks):
{equity_analysis}

Synthesise both analyses into one unified Aureus response for {client_name} / {ticker}.

Use the standard four-section format. Draw on both analyses — the portfolio counsellor's mandate assessment and the equity analyst's thesis input should inform both Key Observations and RM Framing. The response must feel coherent and integrated, not two separate sections stitched together.

Original context:
{context_json}
""",

    "idea-generation": """\
You have received specialist analyses for investment idea generation.

Portfolio Counsellor Analysis (mandate fit, CASA deployment, suitability framing):
{portfolio_analysis}

Equity Analyst Analysis (thesis quality, catalyst strength, conviction):
{equity_analysis}

Synthesise both analyses into one unified Aureus response for {client_name}.

Use the standard four-section format. The equity analyst's thesis assessment and the counsellor's mandate framing must be integrated — surface the best-fit ideas with both investment merit and mandate alignment explained. RM Framing must include the CASA deployment angle if liquidity is present.

Original context:
{context_json}
""",

    "meeting-pack": """\
You have received specialist analyses for a meeting preparation brief.

Portfolio Counsellor Analysis (portfolio posture, open tasks, relationship signals):
{portfolio_analysis}

Equity Analyst Analysis (current stock stories for key holdings):
{equity_analysis}

Synthesise both analyses into one unified Aureus meeting brief for {client_name}.

Use the standard four-section format. The portfolio counsellor leads: what the RM needs to know about the portfolio and relationship. The equity analyst's stock insights should appear where the client is likely to ask about specific names. RM Framing must tell the RM exactly what this meeting must accomplish.

Original context:
{context_json}
""",
}


class AureusOrchestrator:
    """
    Orchestrates internal specialist agents to produce unified Aureus responses.

    Implements the same generate(command, ctx) interface as ClaudeService,
    making it a drop-in replacement in CommandRouter.
    """

    def __init__(
        self,
        portfolio_counsellor,
        equity_analyst,
        financial_analysis,
        claude_service,
    ):
        self.portfolio_counsellor = portfolio_counsellor
        self.equity_analyst = equity_analyst
        self.fa = financial_analysis
        self.claude = claude_service
        logger.info(
            "AureusOrchestrator: ready | solo_portfolio=%d solo_equity=%d collaboration=%d",
            len(_PORTFOLIO_COMMANDS),
            len(_EQUITY_COMMANDS),
            len(_COLLABORATION_COMMANDS),
        )

    async def generate(self, command: str, ctx: dict) -> str:
        """
        Main entry point. Routes to solo agent or collaboration flow.

        Drop-in replacement for ClaudeService.generate(command, ctx).
        """
        if command in _PORTFOLIO_COMMANDS:
            logger.info("Orchestrator → PortfolioCounsellorAgent | command=%s", command)
            return await self.portfolio_counsellor.generate(command, ctx)

        if command in _EQUITY_COMMANDS:
            logger.info("Orchestrator → EquityAnalystAgent | command=%s", command)
            return await self.equity_analyst.generate(command, ctx)

        if command in _COLLABORATION_COMMANDS:
            logger.info("Orchestrator → collaboration | command=%s", command)
            return await self._handle_collaboration(command, ctx)

        # Unknown command — fall through to Claude with default Aureus persona
        logger.warning("Orchestrator: unknown command %s — using default generate", command)
        return await self.claude.generate(command, ctx)

    # ------------------------------------------------------------------
    # Collaboration flow
    # ------------------------------------------------------------------

    async def _handle_collaboration(self, command: str, ctx: dict) -> str:
        """
        Calls both agents in parallel, then synthesises into one Aureus response.
        """
        # Guard: portfolio-fit requires a ticker
        if command == "portfolio-fit":
            ticker = ctx.get("ticker_requested") or ctx.get("ticker", "")
            if not ticker:
                return "❌ Portfolio fit analysis requires a ticker. Usage: `/portfolio_fit [client name] [ticker]`"

        portfolio_ctx, equity_ctx = self._build_agent_contexts(command, ctx)

        results = await asyncio.gather(
            self.portfolio_counsellor.analyze(command, portfolio_ctx),
            self.equity_analyst.analyze(command, equity_ctx),
            return_exceptions=True,
        )

        portfolio_analysis, equity_analysis = results

        # Degrade gracefully if one agent failed
        if isinstance(portfolio_analysis, Exception):
            logger.warning("Portfolio counsellor failed in collaboration | %s", portfolio_analysis)
            portfolio_analysis = "(Portfolio counsellor analysis unavailable)"
        if isinstance(equity_analysis, Exception):
            logger.warning("Equity analyst failed in collaboration | %s", equity_analysis)
            equity_analysis = "(Equity analyst analysis unavailable)"

        logger.info(
            "Orchestrator collaboration complete | command=%s | synthesising",
            command,
        )
        return await self._synthesize(command, ctx, portfolio_analysis, equity_analysis)

    def _build_agent_contexts(self, command: str, ctx: dict) -> tuple[dict, dict]:
        """
        Returns (portfolio_ctx, equity_ctx) for each collaboration command.

        The portfolio counsellor always receives the full client context.
        The equity analyst receives a stock-enriched context where relevant.
        """
        if command == "portfolio-fit":
            # Equity analyst needs the stock thesis/catalyst data for the requested ticker
            ticker = ctx.get("ticker_requested") or ctx.get("ticker", "")
            stock_ctx = self.fa.build_catalyst_context(ticker) if ticker else {}
            equity_ctx = {"ticker": ticker, "is_mock": ctx.get("is_mock", False), **stock_ctx}
            return ctx, equity_ctx

        if command == "idea-generation":
            # Both agents reason over the same context (client + ideas + liquidity)
            return ctx, ctx

        if command == "meeting-pack":
            # Equity analyst receives stock snapshots for the client's top holdings
            top_tickers = [
                h.get("ticker") for h in ctx.get("top_holdings", []) if h.get("ticker")
            ][:3]
            stock_snapshots = {
                t: self.fa.build_financial_snapshot_context(t) for t in top_tickers
            }
            client_name = (
                ctx.get("profile", {}).get("name")
                or ctx.get("customer", {}).get("full_name")
                or "the client"
            )
            equity_ctx = {
                "client_name": client_name,
                "stock_snapshots": stock_snapshots,
                "is_mock": ctx.get("is_mock", False),
            }
            return ctx, equity_ctx

        # Fallback: both agents receive the same context
        return ctx, ctx

    async def _synthesize(
        self,
        command: str,
        ctx: dict,
        portfolio_analysis: str,
        equity_analysis: str,
    ) -> str:
        """
        Final synthesis: merges both analyses into a unified Aureus response.
        Uses the Aureus SYSTEM_PROMPT to ensure consistent tone and output format.
        """
        template = _SYNTHESIS_PROMPTS.get(command)
        if not template:
            # Generic fallback synthesis
            template = (
                "Portfolio Counsellor Analysis:\n{portfolio_analysis}\n\n"
                "Equity Analyst Analysis:\n{equity_analysis}\n\n"
                "Synthesise both into a single unified Aureus response.\n\n"
                "Original context:\n{context_json}"
            )

        # Extract display fields
        customer = ctx.get("profile") or ctx.get("customer", {})
        client_name = (
            customer.get("name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or ctx.get("client_profile", {}).get("name")
            or "the client"
        )
        ticker = ctx.get("ticker_requested") or ctx.get("ticker") or ""
        is_mock = ctx.get("is_mock", False)

        # Build a clean context copy for synthesis (strip is_mock, it's handled via banner)
        ctx_for_synthesis = {k: v for k, v in ctx.items() if k != "is_mock"}

        user_prompt = template.format(
            client_name=client_name,
            ticker=ticker,
            portfolio_analysis=portfolio_analysis,
            equity_analysis=equity_analysis,
            context_json=json.dumps(ctx_for_synthesis, indent=2, default=str),
        )

        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            is_mock=is_mock,
        )
