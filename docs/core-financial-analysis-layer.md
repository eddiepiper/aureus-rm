# Core Financial Analysis Layer

## Overview

`services/financial_analysis_service.py` is the shared foundation for all stock and portfolio reasoning in Aureus. Both the Equity Research Plugin and the Wealth Management Plugin depend on this layer. No command-specific logic lives here.

## Responsibilities

- Shared financial context builders (snapshot, catalyst, thesis, valuation, scenario, compare)
- Stock universe access (`get_stock`, `get_stock_universe`)
- Standardised mock data contract (is_mock, data_freshness, source_label)
- Future-ready abstraction point for live market and news connectors

## Phase 1: Mock Data

All stock data is served from `MOCK_STOCKS` in `services/mock_data.py`. The mock universe covers: DBS, UOB, AAPL, NVDA, TSM.

Every output carries:
```python
{
    "is_mock": True,
    "data_freshness": "framework-based",
    "source_label": "MOCK / NOT REAL-TIME",
    ...
}
```

## Phase 2: Live Connector Insertion

To replace mock data with live MCP connectors:
1. Implement a connector class with the same interface as `MOCK_STOCKS` lookup
2. Pass it as `connector=` to `FinancialAnalysisService.__init__`
3. No callers change — the Core layer handles the swap internally

## Context Builder Reference

| Method | Returns | Used by |
|---|---|---|
| `get_stock(ticker)` | Full mock record or stub | All |
| `get_stock_universe()` | List of available tickers | idea_generation |
| `build_financial_snapshot_context(ticker)` | Snapshot + financials | earnings_deep_dive, thesis_check, morning_note |
| `build_catalyst_context(ticker)` | Snapshot + catalysts + risks + thesis | stock_catalyst, earnings_deep_dive |
| `build_thesis_context(ticker)` | Snapshot + thesis + catalysts + risks + financials | thesis_check, idea_generation |
| `build_valuation_context(ticker)` | Snapshot + financials + thesis | future use |
| `build_scenario_context(ticker)` | Snapshot + scenarios + thesis | portfolio_scenario |
| `build_compare_context(t1, t2)` | Side-by-side for two tickers | future compare command |
