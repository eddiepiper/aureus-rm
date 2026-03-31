"""
services/financial_analysis_service.py

Core Financial Analysis Layer — shared foundation for all stock and portfolio reasoning.

Both the Equity Research Plugin and the Wealth Management Plugin depend on this layer.
Phase 1: all data served from MOCK_STOCKS.
Phase 2+: pass a live `connector` instance to replace mock lookups without changing callers.
"""

from services.mock_data import MOCK_STOCKS

_STUB_TEMPLATE = {
    "is_mock": True,
    "data_freshness": "framework-based",
    "source_label": "MOCK / NOT REAL-TIME",
    "snapshot": {},
    "financials": {},
    "earnings": {},
    "catalysts": [],
    "risks": [],
    "thesis": {"bull_case": "No data available.", "bear_case": "No data available.", "conviction": "Unknown"},
    "scenarios": [],
}


class FinancialAnalysisService:
    """
    Shared financial context builders.

    connector: reserved for Phase 2 live MCP connector. Defaults to None (mock mode).
    """

    def __init__(self, connector=None):
        self._connector = connector

    # ------------------------------------------------------------------
    # Stock universe access
    # ------------------------------------------------------------------

    def get_stock(self, ticker: str) -> dict:
        """Return full mock record for ticker, or a labelled stub if unknown."""
        key = ticker.upper()
        if key in MOCK_STOCKS:
            return MOCK_STOCKS[key]
        stub = dict(_STUB_TEMPLATE)
        stub["ticker"] = key
        stub["snapshot"] = {
            "name": key,
            "sector": "Unknown",
            "geography": "Unknown",
            "market_cap_band": "Unknown",
            "description": f"No mock data available for {key}. Add to MOCK_STOCKS or connect live data.",
        }
        return stub

    def get_stock_universe(self) -> list:
        """Return all tickers available in the mock universe."""
        return list(MOCK_STOCKS.keys())

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def build_financial_snapshot_context(self, ticker: str) -> dict:
        """
        Clean stock snapshot used by earnings_deep_dive, thesis_check, morning_note.
        Returns: ticker, is_mock, data_freshness, source_label, snapshot, financials.
        """
        stock = self.get_stock(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": stock["snapshot"],
            "financials": stock.get("financials", {}),
        }

    def build_catalyst_context(self, ticker: str) -> dict:
        """Catalysts, risks, and conviction level for a ticker."""
        stock = self.get_stock(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": stock["snapshot"],
            "catalysts": stock.get("catalysts", []),
            "risks": stock.get("risks", []),
            "thesis": stock.get("thesis", {}),
        }

    def build_thesis_context(self, ticker: str) -> dict:
        """Bull/bear case, thesis quality flag, supporting catalyst and risk evidence."""
        stock = self.get_stock(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": stock["snapshot"],
            "thesis": stock.get("thesis", {}),
            "catalysts": stock.get("catalysts", []),
            "risks": stock.get("risks", []),
            "financials": stock.get("financials", {}),
        }

    def build_valuation_context(self, ticker: str) -> dict:
        """Key financials snapshot. No real-time prices."""
        stock = self.get_stock(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": stock["snapshot"],
            "financials": stock.get("financials", {}),
            "thesis": stock.get("thesis", {}),
        }

    def build_scenario_context(self, ticker: str) -> dict:
        """Two stress scenarios + impact framing for portfolio scenario use."""
        stock = self.get_stock(ticker)
        return {
            "ticker": stock["ticker"],
            "is_mock": stock["is_mock"],
            "data_freshness": stock["data_freshness"],
            "source_label": stock["source_label"],
            "snapshot": stock["snapshot"],
            "scenarios": stock.get("scenarios", []),
            "thesis": stock.get("thesis", {}),
        }

    def build_compare_context(self, ticker_a: str, ticker_b: str) -> dict:
        """Side-by-side snapshot for two tickers."""
        a = self.get_stock(ticker_a)
        b = self.get_stock(ticker_b)
        return {
            "ticker_a": a["ticker"],
            "ticker_b": b["ticker"],
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "stock_a": {
                "snapshot": a["snapshot"],
                "financials": a.get("financials", {}),
                "thesis": a.get("thesis", {}),
                "catalysts": a.get("catalysts", []),
                "risks": a.get("risks", []),
            },
            "stock_b": {
                "snapshot": b["snapshot"],
                "financials": b.get("financials", {}),
                "thesis": b.get("thesis", {}),
                "catalysts": b.get("catalysts", []),
                "risks": b.get("risks", []),
            },
        }
