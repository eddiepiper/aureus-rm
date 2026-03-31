"""Tests for EquityResearchService (Equity Research Plugin)."""
import pytest
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService


@pytest.fixture
def svc():
    fa = FinancialAnalysisService()
    return EquityResearchService(financial_analysis=fa)


def test_build_earnings_context(svc):
    ctx = svc.build_earnings_context("NVDA")
    assert ctx["ticker"] == "NVDA"
    assert "earnings" in ctx
    assert ctx["earnings"]["beat_miss"] in {"Beat", "Miss", "In-line"}
    assert isinstance(ctx["catalysts"], list)
    assert ctx["is_mock"] is True


def test_build_earnings_context_unknown_ticker(svc):
    ctx = svc.build_earnings_context("ZZZZ")
    assert ctx["ticker"] == "ZZZZ"
    assert ctx["earnings"] == {}
    assert ctx["is_mock"] is True


def test_build_morning_note_context(svc):
    ctx = svc.build_morning_note_context("TSM")
    assert ctx["ticker"] == "TSM"
    assert "snapshot" in ctx
    assert "catalysts" in ctx
    assert "thesis" in ctx
    assert ctx["is_mock"] is True


def test_build_idea_context_screens_universe(svc):
    client_ctx = {
        "profile": {
            "name": "John Tan",
            "risk_profile": "Balanced",
            "objective": "Growth + Income",
            "sector_restrictions": "",
        }
    }
    ctx = svc.build_idea_context(client_ctx)
    assert ctx["is_mock"] is True
    assert "ideas" in ctx
    assert len(ctx["ideas"]) <= 3
    assert "client_profile" in ctx
    assert ctx["client_profile"]["name"] == "John Tan"


def test_build_idea_context_high_conviction_first(svc):
    client_ctx = {"profile": {"name": "Test", "risk_profile": "Growth",
                               "objective": "Growth", "sector_restrictions": ""}}
    ctx = svc.build_idea_context(client_ctx)
    convictions = [idea["conviction"] for idea in ctx["ideas"]]
    order = {"High": 0, "Medium": 1, "Low": 2, "Unknown": 3}
    assert convictions == sorted(convictions, key=lambda c: order.get(c, 3))


def test_build_idea_context_uses_customer_key(svc):
    # Supports raw context with 'customer' key (not just compressed 'profile' key)
    client_ctx = {
        "customer": {
            "preferred_name": "Sarah",
            "risk_profile": "Conservative",
            "investment_objective": "Income",
            "restricted_markets": "China",
        }
    }
    ctx = svc.build_idea_context(client_ctx)
    assert ctx["client_profile"]["name"] == "Sarah"
