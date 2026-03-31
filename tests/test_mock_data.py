"""Tests for MOCK_STOCKS data shape and required fields."""
import pytest
from services.mock_data import MOCK_STOCKS

REQUIRED_TICKERS = ["DBS", "UOB", "AAPL", "NVDA", "TSM"]
REQUIRED_TOP_KEYS = {"ticker", "is_mock", "data_freshness", "source_label",
                     "snapshot", "financials", "earnings", "catalysts", "risks",
                     "thesis", "scenarios"}
REQUIRED_SNAPSHOT_KEYS = {"name", "sector", "geography", "market_cap_band", "description"}
REQUIRED_FINANCIALS_KEYS = {"revenue_ttm", "eps_ttm", "pe_ratio", "pb_ratio", "roe_pct", "div_yield_pct"}
REQUIRED_EARNINGS_KEYS = {"quarter", "revenue_actual", "revenue_est", "eps_actual",
                           "eps_est", "beat_miss", "guidance_direction", "mgmt_tone"}
REQUIRED_THESIS_KEYS = {"bull_case", "bear_case", "conviction"}


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_ticker_present(ticker):
    assert ticker in MOCK_STOCKS, f"{ticker} missing from MOCK_STOCKS"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_top_level_keys(ticker):
    stock = MOCK_STOCKS[ticker]
    missing = REQUIRED_TOP_KEYS - stock.keys()
    assert not missing, f"{ticker} missing keys: {missing}"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_is_mock_flags(ticker):
    stock = MOCK_STOCKS[ticker]
    assert stock["is_mock"] is True
    assert stock["data_freshness"] == "framework-based"
    assert stock["source_label"] == "MOCK / NOT REAL-TIME"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_snapshot_keys(ticker):
    snapshot = MOCK_STOCKS[ticker]["snapshot"]
    missing = REQUIRED_SNAPSHOT_KEYS - snapshot.keys()
    assert not missing, f"{ticker} snapshot missing: {missing}"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_financials_keys(ticker):
    fin = MOCK_STOCKS[ticker]["financials"]
    missing = REQUIRED_FINANCIALS_KEYS - fin.keys()
    assert not missing, f"{ticker} financials missing: {missing}"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_earnings_keys(ticker):
    earn = MOCK_STOCKS[ticker]["earnings"]
    missing = REQUIRED_EARNINGS_KEYS - earn.keys()
    assert not missing, f"{ticker} earnings missing: {missing}"


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_thesis_keys(ticker):
    thesis = MOCK_STOCKS[ticker]["thesis"]
    missing = REQUIRED_THESIS_KEYS - thesis.keys()
    assert not missing, f"{ticker} thesis missing: {missing}"
    assert thesis["conviction"] in {"High", "Medium", "Low"}


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_catalysts_and_risks_are_lists(ticker):
    stock = MOCK_STOCKS[ticker]
    assert isinstance(stock["catalysts"], list) and len(stock["catalysts"]) >= 2
    assert isinstance(stock["risks"], list) and len(stock["risks"]) >= 2


@pytest.mark.parametrize("ticker", REQUIRED_TICKERS)
def test_scenarios_shape(ticker):
    scenarios = MOCK_STOCKS[ticker]["scenarios"]
    assert isinstance(scenarios, list) and len(scenarios) >= 1
    for s in scenarios:
        assert {"name", "impact", "note"} <= s.keys()
