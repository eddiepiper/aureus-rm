"""Tests for FinancialAnalysisService (Core Financial Analysis Layer)."""
import pytest
from services.financial_analysis_service import FinancialAnalysisService

@pytest.fixture
def svc():
    return FinancialAnalysisService()

def test_get_known_stock(svc):
    stock = svc.get_stock("DBS")
    assert stock["ticker"] == "DBS"
    assert stock["is_mock"] is True

def test_get_stock_case_insensitive(svc):
    stock = svc.get_stock("nvda")
    assert stock["ticker"] == "NVDA"

def test_get_unknown_stock_returns_stub(svc):
    stock = svc.get_stock("ZZZZ")
    assert stock["ticker"] == "ZZZZ"
    assert stock["is_mock"] is True
    assert "snapshot" in stock

def test_get_stock_universe_returns_all(svc):
    universe = svc.get_stock_universe()
    assert set(universe) == {"DBS", "UOB", "AAPL", "NVDA", "TSM"}

def test_build_financial_snapshot_context(svc):
    ctx = svc.build_financial_snapshot_context("AAPL")
    assert ctx["ticker"] == "AAPL"
    assert "snapshot" in ctx
    assert "financials" in ctx
    assert ctx["is_mock"] is True

def test_build_catalyst_context(svc):
    ctx = svc.build_catalyst_context("NVDA")
    assert ctx["ticker"] == "NVDA"
    assert isinstance(ctx["catalysts"], list) and len(ctx["catalysts"]) >= 1
    assert isinstance(ctx["risks"], list) and len(ctx["risks"]) >= 1
    assert "thesis" in ctx

def test_build_thesis_context(svc):
    ctx = svc.build_thesis_context("TSM")
    assert ctx["ticker"] == "TSM"
    assert "bull_case" in ctx["thesis"]
    assert "bear_case" in ctx["thesis"]
    assert ctx["thesis"]["conviction"] in {"High", "Medium", "Low"}

def test_build_valuation_context(svc):
    ctx = svc.build_valuation_context("DBS")
    assert ctx["ticker"] == "DBS"
    assert "financials" in ctx
    assert "pe_ratio" in ctx["financials"]

def test_build_scenario_context(svc):
    ctx = svc.build_scenario_context("AAPL")
    assert ctx["ticker"] == "AAPL"
    assert isinstance(ctx["scenarios"], list) and len(ctx["scenarios"]) >= 1
    assert "name" in ctx["scenarios"][0]

def test_build_compare_context(svc):
    ctx = svc.build_compare_context("DBS", "UOB")
    assert ctx["ticker_a"] == "DBS"
    assert ctx["ticker_b"] == "UOB"
    assert "stock_a" in ctx and "stock_b" in ctx
    assert "snapshot" in ctx["stock_a"]
    assert "snapshot" in ctx["stock_b"]

def test_unknown_ticker_compare(svc):
    ctx = svc.build_compare_context("ZZZZ", "DBS")
    assert ctx["ticker_a"] == "ZZZZ"
    assert ctx["stock_a"]["snapshot"]["name"] == "ZZZZ"
