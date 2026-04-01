"""
services/equity_research_service.py

Equity Research Plugin — thin orchestration layer over FinancialAnalysisService.

Does not duplicate stock logic from Core. Composes Core context builders
into command-ready payloads for equity research commands.

Commands served:
  /earnings_deep_dive  -> build_earnings_context
  /morning_note        -> build_morning_note_context
  /idea_generation     -> build_idea_context
  /stock_catalyst      -> FinancialAnalysisService.build_catalyst_context (direct)
  /thesis_check        -> FinancialAnalysisService.build_thesis_context (direct)
"""

from services.financial_analysis_service import FinancialAnalysisService


class EquityResearchService:
    """Thin orchestration layer for equity research commands."""

    def __init__(self, financial_analysis: FinancialAnalysisService):
        self.fa = financial_analysis

    def build_earnings_context(self, ticker: str) -> dict:
        """
        Earnings deep-dive context: snapshot + financials + earnings results + catalysts/risks.
        Used by /earnings_deep_dive.
        """
        stock = self.fa.get_stock(ticker)
        snapshot_ctx = self.fa.build_financial_snapshot_context(ticker)
        catalyst_ctx = self.fa.build_catalyst_context(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": snapshot_ctx["snapshot"],
            "financials": snapshot_ctx["financials"],
            "earnings": stock.get("earnings", {}),
            "catalysts": catalyst_ctx["catalysts"],
            "risks": catalyst_ctx["risks"],
        }

    def build_morning_note_context(self, input_str: str) -> dict:
        """
        Morning note context: snapshot + catalysts + thesis.
        Accepts a ticker or sector name. Sector names without a matching mock
        return a labelled stub.
        Used by /morning_note.
        """
        ticker = input_str.upper().strip()
        stock = self.fa.get_stock(ticker)
        snapshot_ctx = self.fa.build_financial_snapshot_context(ticker)
        catalyst_ctx = self.fa.build_catalyst_context(ticker)
        thesis_ctx = self.fa.build_thesis_context(ticker)
        return {
            "ticker": ticker,
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "snapshot": snapshot_ctx["snapshot"],
            "financials": snapshot_ctx["financials"],
            "catalysts": catalyst_ctx["catalysts"],
            "risks": catalyst_ctx["risks"],
            "thesis": thesis_ctx["thesis"],
        }

    def build_idea_context(self, client_ctx: dict) -> dict:
        """
        Screen the mock stock universe against the client's mandate.
        Returns top 3 ideas sorted by conviction (High -> Medium -> Low).
        Used by /idea_generation.

        client_ctx: accepts either compressed context (has 'profile' key)
                    or raw ClientService context (has 'customer' key).
        """
        profile = client_ctx.get("profile") or {}
        if not profile:
            customer = client_ctx.get("customer", {})
            profile = {
                "name": customer.get("preferred_name") or customer.get("full_name"),
                "risk_profile": customer.get("risk_profile", ""),
                "objective": customer.get("investment_objective", ""),
                "sector_restrictions": customer.get("restricted_markets", ""),
            }

        universe = self.fa.get_stock_universe()
        conviction_order = {"High": 0, "Medium": 1, "Low": 2, "Unknown": 3}

        ideas = []
        for ticker in universe:
            stock = self.fa.get_stock(ticker)
            conviction = stock.get("thesis", {}).get("conviction", "Unknown")
            ideas.append({
                "ticker": ticker,
                "snapshot": stock["snapshot"],
                "thesis": stock.get("thesis", {}),
                "conviction": conviction,
                "catalysts": stock.get("catalysts", [])[:1],
            })

        ideas.sort(key=lambda x: conviction_order.get(x["conviction"], 3))

        existing_tickers = [
            h.get("ticker") for h in client_ctx.get("top_holdings", []) if h.get("ticker")
        ]

        result = {
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "client_profile": {
                "name": profile.get("name"),
                "risk_profile": profile.get("risk_profile", ""),
                "objective": profile.get("objective", ""),
                "sector_restrictions": profile.get("sector_restrictions", ""),
                "deployment_style": profile.get("deployment_style") or client_ctx.get("profile", {}).get("deployment_style"),
            },
            "existing_holdings": existing_tickers,
            "ideas": ideas[:3],
        }

        # Pass deployable liquidity through so Claude can frame ideas as deployment opportunities
        if client_ctx.get("liquidity"):
            result["liquidity"] = client_ctx["liquidity"]

        return result
