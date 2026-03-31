# V3 Equity Research — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 3-layer equity research architecture (Core Financial Analysis → Equity Research Plugin → Wealth Management Plugin) to the Aureus Telegram bot, introducing 6 new V3 commands while preserving all V2 commands unchanged.

**Architecture:** `FinancialAnalysisService` is the shared stock data and reasoning foundation. `EquityResearchService` is a thin orchestration layer on top of it for equity-specific commands. The Wealth Management Plugin (existing `ClientService` + new `portfolio_scenario`) uses `FinancialAnalysisService` for scenario framing. All stock data is mock/framework-based in Phase 1 — live connectors plug in at the Core layer in Phase 2.

**Tech Stack:** Python 3.10+, python-telegram-bot 20.7, anthropic 0.40.0, pytest, python-dotenv

---

## File Map

### New files
| File | Layer | Responsibility |
|---|---|---|
| `services/financial_analysis_service.py` | Core | Shared stock context builders; mock universe lookup; future connector abstraction |
| `services/equity_research_service.py` | Equity Plugin | Thin orchestration: `build_earnings_context`, `build_morning_note_context`, `build_idea_context` |
| `tests/__init__.py` | — | Make tests a package |
| `tests/test_financial_analysis_service.py` | Core | Unit tests for all 8 Core methods |
| `tests/test_equity_research_service.py` | Equity Plugin | Unit tests for 3 plugin methods |
| `skills/financial-analysis-core.md` | Core | Skill reference: shared financial reasoning |
| `skills/earnings-analysis-framework.md` | Equity | Skill reference: earnings reasoning |
| `skills/catalyst-analysis-framework.md` | Equity | Skill reference: catalyst framing |
| `skills/thesis-analysis-framework.md` | Equity | Skill reference: bull/bear thesis |
| `skills/idea-generation-framework.md` | Equity | Skill reference: mandate-aware idea screening |
| `skills/morning-note-framework.md` | Equity | Skill reference: morning note structure |
| `skills/portfolio-scenario-thinking.md` | Wealth | Skill reference: portfolio scenario reasoning |
| `docs/core-financial-analysis-layer.md` | Core | Architecture doc for Core layer |
| `docs/equity-research-plugin.md` | Equity | Architecture doc for Equity plugin |
| `docs/portfolio-intelligence.md` | Wealth | Architecture doc for WM plugin |

### Modified files
| File | Change |
|---|---|
| `services/mock_data.py` | Add `MOCK_STOCKS` dict (5 tickers) |
| `services/command_router.py` | Inject new services; add 6 V3 handlers |
| `services/claude_service.py` | Add 6 V3 command prompts |
| `services/response_formatter.py` | Add 6 V3 template fallbacks |
| `bot/telegram_bot.py` | Register 6 slash commands; update help text |
| `services/chat_router.py` | Add NL intents + arg extraction for 6 commands |
| `app.py` | Instantiate `FinancialAnalysisService` + `EquityResearchService`; pass to router |

---

## Task 1: Add MOCK_STOCKS to mock_data.py

**Files:**
- Modify: `services/mock_data.py`
- Create: `tests/__init__.py`
- Create: `tests/test_mock_data.py`

- [ ] **Step 1: Create tests package**

```bash
mkdir -p /Users/edwardchiang/aureus-rm/tests
touch /Users/edwardchiang/aureus-rm/tests/__init__.py
```

- [ ] **Step 2: Write failing tests for MOCK_STOCKS shape**

Create `tests/test_mock_data.py`:

```python
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
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_mock_data.py -v 2>&1 | head -30
```
Expected: `ImportError` or `KeyError` — `MOCK_STOCKS` does not exist yet.

- [ ] **Step 4: Add MOCK_STOCKS to mock_data.py**

Append to the bottom of `services/mock_data.py`:

```python

# ---------------------------------------------------------------------------
# V3 — Mock stock universe (Phase 1)
# All data is framework-based and NOT real-time. Clearly labelled for RM use.
# ---------------------------------------------------------------------------

MOCK_STOCKS: dict[str, dict] = {
    "DBS": {
        "ticker": "DBS",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "DBS Group Holdings",
            "sector": "Financials",
            "geography": "Singapore",
            "market_cap_band": "Large Cap",
            "description": (
                "DBS Group is Southeast Asia's largest bank by assets, offering commercial "
                "banking, treasury, and wealth management services. Primary revenue from "
                "net interest income and fee-based wealth services."
            ),
        },
        "financials": {
            "revenue_ttm": "SGD 21.2B",
            "eps_ttm": "SGD 3.82",
            "pe_ratio": "9.5x",
            "pb_ratio": "1.6x",
            "roe_pct": "17.8%",
            "div_yield_pct": "5.8%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "SGD 5.8B",
            "revenue_est": "SGD 5.6B",
            "eps_actual": "SGD 1.02",
            "eps_est": "SGD 0.98",
            "beat_miss": "Beat",
            "guidance_direction": "Maintained",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "Rate environment supports NIM stability through 2025",
            "Wealth management AUM growth from regional HNW client flows",
            "Capital return programme — ongoing buybacks and dividend growth",
        ],
        "risks": [
            "NIM compression if rates are cut faster than expected",
            "Regional asset quality risk from China/HK property sector exposure",
        ],
        "thesis": {
            "bull_case": (
                "Best-in-class ROE in Singapore banking, strong capital position, "
                "and wealth management growth trajectory support premium valuation."
            ),
            "bear_case": (
                "Rate cuts will compress NIM materially; China property exposure "
                "remains an unresolved tail risk."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "Rapid rate cuts (100bps)",
                "impact": "Negative",
                "note": "NIM compression of ~20bps; earnings impact estimated at ~8% reduction.",
            },
            {
                "name": "Regional credit tightening",
                "impact": "Negative",
                "note": "Rising NPLs from SEA SME segment could require material provision build-up.",
            },
        ],
    },

    "UOB": {
        "ticker": "UOB",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "United Overseas Bank",
            "sector": "Financials",
            "geography": "Singapore / ASEAN",
            "market_cap_band": "Large Cap",
            "description": (
                "UOB is a leading ASEAN bank with strong retail and SME franchise "
                "across Singapore, Thailand, Malaysia, Indonesia, and Vietnam. "
                "Focus on ASEAN connectivity, trade finance, and regional expansion."
            ),
        },
        "financials": {
            "revenue_ttm": "SGD 14.1B",
            "eps_ttm": "SGD 2.94",
            "pe_ratio": "8.8x",
            "pb_ratio": "1.2x",
            "roe_pct": "14.2%",
            "div_yield_pct": "5.1%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "SGD 3.7B",
            "revenue_est": "SGD 3.6B",
            "eps_actual": "SGD 0.76",
            "eps_est": "SGD 0.74",
            "beat_miss": "Beat",
            "guidance_direction": "Maintained",
            "mgmt_tone": "Neutral",
        },
        "catalysts": [
            "Citi ASEAN integration nearing completion — cost synergies materialising",
            "ASEAN trade finance growth driven by supply chain relocation trends",
            "Digital banking expansion reducing cost-to-income ratio",
        ],
        "risks": [
            "Citi integration costs and execution risk remain elevated",
            "ASEAN credit cycle risk — rising household leverage in Thailand and Indonesia",
        ],
        "thesis": {
            "bull_case": (
                "ASEAN franchise and Citi acquisition create a differentiated regional bank "
                "with an improving ROE trajectory as integration costs normalise."
            ),
            "bear_case": (
                "Integration overhang, lower ROE vs. DBS, and ASEAN credit cycle risk "
                "cap near-term re-rating potential."
            ),
            "conviction": "Medium",
        },
        "scenarios": [
            {
                "name": "ASEAN growth slowdown",
                "impact": "Negative",
                "note": "Loan growth below 5% would pressure revenue; integration costs not yet recovered.",
            },
            {
                "name": "Citi integration delays",
                "impact": "Negative",
                "note": "Extended integration timeline increases execution risk and extends cost drag.",
            },
        ],
    },

    "AAPL": {
        "ticker": "AAPL",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "Apple Inc.",
            "sector": "Technology",
            "geography": "United States",
            "market_cap_band": "Mega Cap",
            "description": (
                "Apple designs and sells consumer electronics, software, and services "
                "including iPhone, Mac, iPad, wearables, and a growing services segment "
                "(App Store, iCloud, Apple TV+, Apple Pay). Services now exceed 25% of revenue."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 391B",
            "eps_ttm": "USD 6.57",
            "pe_ratio": "28.5x",
            "pb_ratio": "45.2x",
            "roe_pct": "160.9%",
            "div_yield_pct": "0.5%",
        },
        "earnings": {
            "quarter": "Q4 FY2025",
            "revenue_actual": "USD 94.9B",
            "revenue_est": "USD 94.1B",
            "eps_actual": "USD 1.64",
            "eps_est": "USD 1.60",
            "beat_miss": "Beat",
            "guidance_direction": "In-line",
            "mgmt_tone": "Neutral",
        },
        "catalysts": [
            "Apple Intelligence AI feature rollout driving upgrade cycle into FY2026",
            "Services segment margin expansion improving overall earnings quality",
            "India manufacturing ramp reducing US tariff exposure",
        ],
        "risks": [
            "China revenue (~18% of total) faces ongoing geopolitical and regulatory risk",
            "iPhone unit growth stagnating in core markets — upgrade cycle elongation",
        ],
        "thesis": {
            "bull_case": (
                "Services mix shift drives margin expansion and earnings quality; "
                "AI-driven upgrade supercycle could re-accelerate iPhone growth in FY2026–27."
            ),
            "bear_case": (
                "Premium valuation leaves little room for error; China risk and elongating "
                "upgrade cycles could compress multiples meaningfully."
            ),
            "conviction": "Medium",
        },
        "scenarios": [
            {
                "name": "China revenue disruption",
                "impact": "Negative",
                "note": "15% China revenue decline reduces group EPS by approximately 6%.",
            },
            {
                "name": "AI upgrade cycle underdelivers",
                "impact": "Negative",
                "note": "Flat iPhone units in FY2026 would disappoint consensus and pressure the multiple.",
            },
        ],
    },

    "NVDA": {
        "ticker": "NVDA",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "NVIDIA Corporation",
            "sector": "Technology",
            "geography": "United States",
            "market_cap_band": "Mega Cap",
            "description": (
                "NVIDIA designs GPUs and system-on-chip units. The Data Center segment "
                "(Hopper/Blackwell architectures) now dominates revenue, driven by AI training "
                "and inference demand from hyperscalers and enterprises."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 113B",
            "eps_ttm": "USD 2.53",
            "pe_ratio": "38.2x",
            "pb_ratio": "28.4x",
            "roe_pct": "123.8%",
            "div_yield_pct": "0.03%",
        },
        "earnings": {
            "quarter": "Q3 FY2026",
            "revenue_actual": "USD 35.1B",
            "revenue_est": "USD 33.2B",
            "eps_actual": "USD 0.89",
            "eps_est": "USD 0.84",
            "beat_miss": "Beat",
            "guidance_direction": "Raised",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "Blackwell architecture ramp — production yields improving, backlog clearing",
            "Sovereign AI and enterprise inference broadening demand beyond hyperscalers",
            "CUDA ecosystem lock-in remains a durable competitive moat",
        ],
        "risks": [
            "Valuation prices in significant future growth — any execution miss is severely punished",
            "Export controls to China limit a material revenue opportunity; regulatory risk remains elevated",
        ],
        "thesis": {
            "bull_case": (
                "AI compute infrastructure is a multi-year secular theme; NVDA is the dominant "
                "picks-and-shovels play with unmatched ecosystem and software advantages."
            ),
            "bear_case": (
                "Hyperscaler capex cycles are volatile; AMD and custom silicon competition "
                "is intensifying; current valuation requires flawless execution for years."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "AI capex pullback (20% cut)",
                "impact": "Very Negative",
                "note": "Hyperscaler capex cut would compress revenue growth and materially reset consensus.",
            },
            {
                "name": "Export control tightening",
                "impact": "Negative",
                "note": "Expanded China restrictions could remove ~10–15% of addressable market.",
            },
        ],
    },

    "TSM": {
        "ticker": "TSM",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "Taiwan Semiconductor Manufacturing Company",
            "sector": "Technology",
            "geography": "Taiwan / United States",
            "market_cap_band": "Large Cap",
            "description": (
                "TSMC is the world's largest dedicated contract chip manufacturer, producing "
                "chips for Apple, NVIDIA, AMD, and Qualcomm. Controls ~60% of global foundry "
                "revenue and over 90% of leading-edge node capacity."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 88B",
            "eps_ttm": "USD 6.72",
            "pe_ratio": "22.4x",
            "pb_ratio": "6.8x",
            "roe_pct": "30.2%",
            "div_yield_pct": "1.4%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "USD 23.5B",
            "revenue_est": "USD 22.9B",
            "eps_actual": "USD 1.81",
            "eps_est": "USD 1.75",
            "beat_miss": "Beat",
            "guidance_direction": "Raised",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "AI chip demand driving N3/N2 node utilisation from NVDA, AAPL, and custom silicon",
            "US fab buildout (Arizona) mitigates geopolitical risk and supports diversification",
            "Pricing power at leading nodes maintained — margins trending upward",
        ],
        "risks": [
            "Taiwan geopolitical risk is the primary overhang — impossible to fully hedge",
            "CapEx intensity is high and rising — free cash flow constrained during investment cycle",
        ],
        "thesis": {
            "bull_case": (
                "AI chip demand creates a multi-year capacity constraint at leading nodes; "
                "TSMC is the irreplaceable manufacturer with structural pricing power."
            ),
            "bear_case": (
                "Geopolitical risk is unquantifiable and could cause rapid multiple de-rating; "
                "CapEx cycle delays FCF recovery timeline."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "Taiwan strait escalation",
                "impact": "Severe",
                "note": "Geopolitical escalation causes immediate multiple compression and global supply chain disruption.",
            },
            {
                "name": "AI demand deceleration",
                "impact": "Moderate Negative",
                "note": "N3/N2 utilisation softening compresses margins and requires capex revision.",
            },
        ],
    },
}
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_mock_data.py -v
```
Expected: All 40 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/mock_data.py tests/__init__.py tests/test_mock_data.py
git commit -m "feat: add MOCK_STOCKS universe (DBS, UOB, AAPL, NVDA, TSM) for V3 equity research"
```

---

## Task 2: Create FinancialAnalysisService (Core Layer)

**Files:**
- Create: `services/financial_analysis_service.py`
- Create: `tests/test_financial_analysis_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_financial_analysis_service.py`:

```python
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
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_financial_analysis_service.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'services.financial_analysis_service'`

- [ ] **Step 3: Create services/financial_analysis_service.py**

```python
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

    def get_stock_universe(self) -> list[str]:
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_financial_analysis_service.py -v
```
Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/financial_analysis_service.py tests/test_financial_analysis_service.py
git commit -m "feat: add FinancialAnalysisService — Core Financial Analysis Layer"
```

---

## Task 3: Create EquityResearchService (Equity Research Plugin)

**Files:**
- Create: `services/equity_research_service.py`
- Create: `tests/test_equity_research_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_equity_research_service.py`:

```python
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


def test_build_idea_context_uses_compressed_client_ctx(svc):
    # Supports both 'profile' key (compressed) and 'customer' key (raw)
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
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_equity_research_service.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'services.equity_research_service'`

- [ ] **Step 3: Create services/equity_research_service.py**

```python
"""
services/equity_research_service.py

Equity Research Plugin — thin orchestration layer over FinancialAnalysisService.

Does not duplicate stock logic from Core. Composes Core context builders
into command-ready payloads for equity research commands.

Commands served:
  /earnings_deep_dive  → build_earnings_context
  /morning_note        → build_morning_note_context
  /idea_generation     → build_idea_context
  /stock_catalyst      → FinancialAnalysisService.build_catalyst_context (direct)
  /thesis_check        → FinancialAnalysisService.build_thesis_context (direct)
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
        Returns top 3 ideas sorted by conviction (High → Medium → Low).
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

        return {
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "client_profile": {
                "name": profile.get("name"),
                "risk_profile": profile.get("risk_profile", ""),
                "objective": profile.get("objective", ""),
                "sector_restrictions": profile.get("sector_restrictions", ""),
            },
            "ideas": ideas[:3],
        }
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/test_equity_research_service.py -v
```
Expected: All 6 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/equity_research_service.py tests/test_equity_research_service.py
git commit -m "feat: add EquityResearchService — Equity Research Plugin orchestration layer"
```

---

## Task 4: Add V3 Claude Prompts

**Files:**
- Modify: `services/claude_service.py`

- [ ] **Step 1: Add 6 entries to COMMAND_PROMPTS in claude_service.py**

In `services/claude_service.py`, add to the `COMMAND_PROMPTS` dict after the existing 4 entries:

```python
    "earnings-deep-dive": """\
Earnings deep-dive for {ticker}.

Use the four-section format. Snapshot = what this company does in one line. \
Key Observations = what this quarter's results mean — beat/miss, guidance direction, \
and the one thing that changed vs. prior narrative. Key Risks = 2 risks the RM \
should be ready to discuss. RM Framing = one sentence on how to position this \
with a client who holds or is watching this name.

Note: {source_label}

Earnings context:
{context_json}
""",

    "stock-catalyst": """\
Stock catalyst brief for {ticker}.

Use the four-section format. Snapshot = what the company does and its conviction level. \
Key Observations = the 2–3 near-term catalysts most relevant to an RM conversation. \
Key Risks = top 2 risks that could undercut the catalyst thesis. \
RM Framing = one sentence on how to introduce these catalysts in a client conversation.

Note: {source_label}

Catalyst context:
{context_json}
""",

    "thesis-check": """\
Thesis check for {ticker}.

Use the four-section format. Snapshot = one line on what the company does and current \
conviction. Key Observations = the bull case and bear case, each in one sentence. \
Key Risks = the 1–2 factors that most threaten the thesis right now. \
RM Framing = how the RM should position this name — when to raise it and when to hold back.

Note: {source_label}

Thesis context:
{context_json}
""",

    "idea-generation": """\
Generate stock ideas for {client_name}.

Use the four-section format. Snapshot = the client's mandate in one line. \
Key Observations = the 2–3 highest-conviction ideas from the universe \
that fit this client's risk profile and objective, with a one-line rationale each. \
Key Risks = the most important risk to flag for this client given their profile. \
RM Framing = how the RM should open the idea conversation with this client.

Note: {source_label}

Client and idea context:
{context_json}
""",

    "morning-note": """\
Morning note for {ticker}.

Use the four-section format. Snapshot = what this name is and where it sits in the \
current market narrative. Key Observations = the 2–3 things an RM should know about \
this name going into today's conversations. Key Risks = what could move against this \
name near-term. RM Framing = one sentence on how to surface this in a morning client \
touchpoint.

Note: {source_label}

Morning note context:
{context_json}
""",

    "portfolio-scenario": """\
Portfolio scenario analysis for {client_name}.

Use the four-section format. Snapshot = the client's portfolio posture in one line. \
Key Observations = the 2–3 most significant scenario exposures across the portfolio \
— which holdings are most vulnerable and to what. Key Risks = the scenario that would \
cause the most damage to this client's mandate and why. \
RM Framing = how the RM should open a scenario conversation — framing risk without \
alarming the client.

Note: {source_label}

Portfolio and scenario context:
{context_json}
""",
```

- [ ] **Step 2: Update _build_user_prompt to handle V3 context shapes**

In `services/claude_service.py`, the `_build_user_prompt` method currently reads `client_name` from `profile` or `customer`. For ticker-only commands it should read `ticker` from `ctx`. Replace the `_build_user_prompt` method with:

```python
    def _build_user_prompt(self, command: str, ctx: dict) -> str:
        template = COMMAND_PROMPTS.get(command)
        if not template:
            return (
                f"Run {command} for this context.\n\n"
                f"Context:\n{json.dumps(ctx, indent=2, default=str)}"
            )

        # Client name — works for both compressed and raw context shapes
        customer = ctx.get("profile") or ctx.get("customer", {})
        client_name = (
            customer.get("name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or ctx.get("client_profile", {}).get("name")
            or "the client"
        )

        # Ticker — direct key or from nested client_profile context
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
```

- [ ] **Step 3: Smoke test prompt generation (no API call)**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
from services.claude_service import ClaudeService
svc = ClaudeService(api_key='test')
from services.financial_analysis_service import FinancialAnalysisService
fa = FinancialAnalysisService()
ctx = fa.build_catalyst_context('NVDA')
prompt = svc._build_user_prompt('stock-catalyst', ctx)
print(prompt[:300])
print('---OK')
"
```
Expected: Prints first 300 chars of a valid prompt ending with `---OK`.

- [ ] **Step 4: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/claude_service.py
git commit -m "feat: add 6 V3 Claude command prompts (earnings, catalyst, thesis, ideas, morning note, scenario)"
```

---

## Task 5: Add V3 Template Fallbacks

**Files:**
- Modify: `services/response_formatter.py`

- [ ] **Step 1: Append 6 fallback formatters to response_formatter.py**

Add to the bottom of `services/response_formatter.py`:

```python

# ---------------------------------------------------------------------------
# V3 — Equity Research Plugin fallbacks
# Used when Claude API is unavailable. Returns structured template output.
# ---------------------------------------------------------------------------

def _mock_banner_equity(ctx: dict) -> str:
    label = ctx.get("source_label", "MOCK / NOT REAL-TIME")
    return f"⚠️ *{label}*\n\n"


def format_earnings_deep_dive(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    earnings = ctx.get("earnings", {})
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Earnings Deep Dive — {ticker}*")
    lines.append("")
    lines.append(f"*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | {snap.get('geography', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    if earnings:
        lines.append(f"- {earnings.get('quarter', 'N/A')}: Revenue {earnings.get('revenue_actual', 'N/A')} vs est {earnings.get('revenue_est', 'N/A')} — {earnings.get('beat_miss', 'N/A')}")
        lines.append(f"- EPS {earnings.get('eps_actual', 'N/A')} vs est {earnings.get('eps_est', 'N/A')} | Guidance: {earnings.get('guidance_direction', 'N/A')}")
        lines.append(f"- Management tone: {earnings.get('mgmt_tone', 'N/A')}")
    else:
        lines.append("- Earnings data not available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    if catalysts:
        lines.append(f"- Key near-term catalyst: {catalysts[0]}")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_stock_catalyst(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    thesis = ctx.get("thesis", {})
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Stock Catalyst — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | Conviction: {thesis.get('conviction', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    for c in catalysts[:3]:
        lines.append(f"- {c}")
    if not catalysts:
        lines.append("- No catalyst data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append(f"- Use these catalysts to frame a forward-looking conversation about {ticker}.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_thesis_check(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    thesis = ctx.get("thesis", {})
    risks = ctx.get("risks", [])
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Thesis Check — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | Conviction: {thesis.get('conviction', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    if thesis.get("bull_case"):
        lines.append(f"- Bull: {thesis['bull_case']}")
    if thesis.get("bear_case"):
        lines.append(f"- Bear: {thesis['bear_case']}")
    if not thesis:
        lines.append("- No thesis data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append(f"- Raise {ticker} when conviction is High and client mandate aligns with the bull case.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_idea_generation(ctx: dict) -> str:
    ideas = ctx.get("ideas", [])
    profile = ctx.get("client_profile", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Idea Generation — {profile.get('name', 'Client')}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {profile.get('risk_profile', 'N/A')} | {profile.get('objective', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    for idea in ideas[:3]:
        snap = idea.get("snapshot", {})
        conviction = idea.get("conviction", "N/A")
        lines.append(f"- {idea['ticker']} ({snap.get('sector', 'N/A')}) — Conviction: {conviction}")
        if idea.get("catalysts"):
            lines.append(f"  Key catalyst: {idea['catalysts'][0]}")
    if not ideas:
        lines.append("- No ideas available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    lines.append("- Validate each idea against client suitability before raising. Use /thesis_check [ticker] for detail.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append("- Present ideas as conversation starters, not recommendations.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_morning_note(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    thesis = ctx.get("thesis", {})
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Morning Note — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | {snap.get('geography', 'N/A')}")
    if snap.get("description"):
        lines.append(f"- {snap['description'][:120]}...")
    lines.append("")
    lines.append("*Key Observations*")
    for c in catalysts[:3]:
        lines.append(f"- {c}")
    if not catalysts:
        lines.append("- No catalyst data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    conviction = thesis.get("conviction", "N/A")
    lines.append(f"- Internal conviction: {conviction}. Surface this in morning client touchpoints where mandate allows.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_portfolio_scenario(ctx: dict) -> str:
    client_name = ctx.get("client_name", "Client")
    scenarios_by_ticker = ctx.get("scenarios_by_ticker", [])
    profile = ctx.get("profile", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Portfolio Scenario — {client_name}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {profile.get('risk_profile', 'N/A')} | {profile.get('objective', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    shown = 0
    for item in scenarios_by_ticker:
        if shown >= 3:
            break
        ticker = item.get("ticker", "")
        for s in item.get("scenarios", [])[:1]:
            lines.append(f"- {ticker}: {s['name']} → {s['impact']}. {s['note']}")
            shown += 1
    if shown == 0:
        lines.append("- No scenario data available for current holdings.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    lines.append("- Review concentration in high-impact scenario names before next client meeting.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append("- Frame scenarios as preparedness, not predictions. Focus on what the RM can action now.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)
```

- [ ] **Step 2: Smoke test all 6 formatters**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
from services import response_formatter as fmt

fa = FinancialAnalysisService()
er = EquityResearchService(financial_analysis=fa)

# Test each formatter
ctx1 = er.build_earnings_context('NVDA')
print(fmt.format_earnings_deep_dive(ctx1)[:200])
print('---')
ctx2 = fa.build_catalyst_context('TSM')
print(fmt.format_stock_catalyst(ctx2)[:200])
print('---')
ctx3 = fa.build_thesis_context('AAPL')
print(fmt.format_thesis_check(ctx3)[:200])
print('---')
client_ctx = {'profile': {'name': 'John', 'risk_profile': 'Balanced', 'objective': 'Growth', 'sector_restrictions': ''}}
ctx4 = er.build_idea_context(client_ctx)
print(fmt.format_idea_generation(ctx4)[:200])
print('---')
ctx5 = er.build_morning_note_context('DBS')
print(fmt.format_morning_note(ctx5)[:200])
print('ALL OK')
"
```
Expected: 5 formatted outputs printed, ending with `ALL OK`.

- [ ] **Step 3: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/response_formatter.py
git commit -m "feat: add 6 V3 template fallback formatters for equity research commands"
```

---

## Task 6: Add V3 Handlers to CommandRouter

**Files:**
- Modify: `services/command_router.py`

- [ ] **Step 1: Update __init__ to accept new services**

In `services/command_router.py`, update the `CommandRouter.__init__` signature and body:

```python
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
```

Add to the import block at the top of the file, then update `__init__`:

```python
    def __init__(
        self,
        client_service: ClientService,
        claude_service=None,
        sheets_service: Optional[SheetsService] = None,
        financial_analysis: Optional[FinancialAnalysisService] = None,
        equity_research: Optional[EquityResearchService] = None,
    ):
        self.client = client_service
        self.claude = claude_service
        self.sheets = sheets_service
        self.fa = financial_analysis
        self.er = equity_research

        if self.claude:
            logger.info("CommandRouter: Claude API enabled")
        else:
            logger.info("CommandRouter: no Claude API — using template responses")
        if self.fa:
            logger.info("CommandRouter: FinancialAnalysisService attached")
        if self.er:
            logger.info("CommandRouter: EquityResearchService attached")
```

- [ ] **Step 2: Add V3 commands to the route() handlers dict**

In the `route()` method, update the `handlers` dict:

```python
        handlers = {
            # V2 — unchanged
            "client-review":    self._client_review,
            "portfolio-fit":    self._portfolio_fit,
            "meeting-pack":     self._meeting_pack,
            "next-best-action": self._next_best_action,
            # V3 — Equity Research Plugin
            "earnings-deep-dive":  self._earnings_deep_dive,
            "stock-catalyst":      self._stock_catalyst,
            "thesis-check":        self._thesis_check,
            "idea-generation":     self._idea_generation,
            "morning-note":        self._morning_note,
            # V3 — Wealth Management Plugin
            "portfolio-scenario":  self._portfolio_scenario,
        }
```

Also update the "unknown command" message to list all 10 commands:

```python
        if handler is None:
            return (
                f"Unknown command: `/{command}`\n\n"
                "V2: /client\\_review · /portfolio\\_fit · /meeting\\_pack · /next\\_best\\_action\n"
                "V3 Equity: /earnings\\_deep\\_dive · /stock\\_catalyst · /thesis\\_check · "
                "/idea\\_generation · /morning\\_note\n"
                "V3 Wealth: /portfolio\\_scenario"
            )
```

- [ ] **Step 3: Update _generate to include V3 formatters**

In the `_generate` method, update the `formatters` dict:

```python
        formatters = {
            # V2
            "client-review":    fmt.format_client_review,
            "portfolio-fit":    fmt.format_portfolio_fit,
            "meeting-pack":     fmt.format_meeting_pack,
            "next-best-action": fmt.format_next_best_action,
            # V3 Equity
            "earnings-deep-dive":  fmt.format_earnings_deep_dive,
            "stock-catalyst":      fmt.format_stock_catalyst,
            "thesis-check":        fmt.format_thesis_check,
            "idea-generation":     fmt.format_idea_generation,
            "morning-note":        fmt.format_morning_note,
            # V3 Wealth
            "portfolio-scenario":  fmt.format_portfolio_scenario,
        }
```

- [ ] **Step 4: Add 6 V3 command handlers**

Append these handlers after the existing V2 handlers in `command_router.py`:

```python
    # ------------------------------------------------------------------
    # V3 — Equity Research Plugin handlers
    # ------------------------------------------------------------------

    async def _earnings_deep_dive(self, args: list[str]) -> str:
        if not args:
            return "Usage: `/earnings_deep_dive [ticker]`\nExample: `/earnings_deep_dive NVDA`"
        ticker = args[0].upper()
        if not self.er:
            return "❌ EquityResearchService not available."
        ctx = self.er.build_earnings_context(ticker)
        return await self._generate("earnings-deep-dive", ctx)

    async def _stock_catalyst(self, args: list[str]) -> str:
        if not args:
            return "Usage: `/stock_catalyst [ticker]`\nExample: `/stock_catalyst TSM`"
        ticker = args[0].upper()
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        ctx = self.fa.build_catalyst_context(ticker)
        return await self._generate("stock-catalyst", ctx)

    async def _thesis_check(self, args: list[str]) -> str:
        if not args:
            return "Usage: `/thesis_check [ticker]`\nExample: `/thesis_check AAPL`"
        ticker = args[0].upper()
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        ctx = self.fa.build_thesis_context(ticker)
        return await self._generate("thesis-check", ctx)

    async def _idea_generation(self, args: list[str]) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/idea_generation [client name]`\nExample: `/idea_generation John Tan`"
        if not self.er:
            return "❌ EquityResearchService not available."
        client_ctx = self.client.build_client_review_context(name)
        compressed = self._compress_context(client_ctx)
        ctx = self.er.build_idea_context(compressed)
        return await self._generate("idea-generation", ctx)

    async def _morning_note(self, args: list[str]) -> str:
        if not args:
            return "Usage: `/morning_note [ticker or sector]`\nExample: `/morning_note DBS`"
        input_str = args[0].upper()
        if not self.er:
            return "❌ EquityResearchService not available."
        ctx = self.er.build_morning_note_context(input_str)
        return await self._generate("morning-note", ctx)

    # ------------------------------------------------------------------
    # V3 — Wealth Management Plugin handler
    # ------------------------------------------------------------------

    async def _portfolio_scenario(self, args: list[str]) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/portfolio_scenario [client name]`\nExample: `/portfolio_scenario John Tan`"
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        client_ctx = self.client.build_client_review_context(name)
        compressed = self._compress_context(client_ctx)

        # Build scenario context for each held ticker
        held_tickers = [h["ticker"] for h in compressed.get("top_holdings", []) if h.get("ticker")]
        scenarios_by_ticker = [
            {"ticker": t, **self.fa.build_scenario_context(t)}
            for t in held_tickers
        ]

        ctx = {
            "client_name": compressed.get("profile", {}).get("name", name),
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "profile": compressed.get("profile", {}),
            "top_holdings": compressed.get("top_holdings", []),
            "scenarios_by_ticker": scenarios_by_ticker,
        }
        return await self._generate("portfolio-scenario", ctx)
```

- [ ] **Step 5: Smoke test routing (no Telegram, no API)**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
import asyncio
from services.mock_data import MOCK_CUSTOMER, MOCK_HOLDINGS, MOCK_INTERACTIONS, MOCK_TASKS, MOCK_WATCHLIST
from services.client_service import ClientService
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
from services.command_router import CommandRouter

fa = FinancialAnalysisService()
er = EquityResearchService(financial_analysis=fa)
cs = ClientService(sheets=None, use_mock=True)
router = CommandRouter(client_service=cs, financial_analysis=fa, equity_research=er)

async def test():
    r1 = await router.route('earnings-deep-dive', ['NVDA'])
    print('earnings-deep-dive:', r1[:100])
    r2 = await router.route('stock-catalyst', ['TSM'])
    print('stock-catalyst:', r2[:100])
    r3 = await router.route('thesis-check', ['AAPL'])
    print('thesis-check:', r3[:100])
    r4 = await router.route('idea-generation', ['John', 'Tan'])
    print('idea-generation:', r4[:100])
    r5 = await router.route('morning-note', ['DBS'])
    print('morning-note:', r5[:100])
    r6 = await router.route('portfolio-scenario', ['John', 'Tan'])
    print('portfolio-scenario:', r6[:100])
    print('ALL V3 routes OK')

asyncio.run(test())
"
```
Expected: 6 responses printed, ending with `ALL V3 routes OK`.

- [ ] **Step 6: Confirm V2 routes still work**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
import asyncio
from services.client_service import ClientService
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
from services.command_router import CommandRouter

fa = FinancialAnalysisService()
er = EquityResearchService(financial_analysis=fa)
cs = ClientService(sheets=None, use_mock=True)
router = CommandRouter(client_service=cs, financial_analysis=fa, equity_research=er)

async def test():
    r = await router.route('client-review', ['John', 'Tan'])
    assert 'John' in r, 'client-review broken'
    r = await router.route('next-best-action', ['John', 'Tan'])
    assert r, 'next-best-action broken'
    print('V2 routes intact')

asyncio.run(test())
"
```
Expected: `V2 routes intact`

- [ ] **Step 7: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/command_router.py
git commit -m "feat: add 6 V3 command handlers to CommandRouter; preserve all V2 handlers"
```

---

## Task 7: Register V3 Commands in Telegram Bot

**Files:**
- Modify: `bot/telegram_bot.py`

- [ ] **Step 1: Update HELP_TEXT**

Replace the existing `HELP_TEXT` constant in `bot/telegram_bot.py` with:

```python
HELP_TEXT = """
*Aureus RM Copilot — V3*

*V2 — Client & Portfolio*
/client\\_review [name] — Full client review
/portfolio\\_fit [name] [ticker] — Portfolio fit check
/meeting\\_pack [name] — Meeting prep pack
/next\\_best\\_action [name] — Suggested next actions

*V3 — Equity Research*
/earnings\\_deep\\_dive [ticker] — Earnings results deep dive
/stock\\_catalyst [ticker] — Near-term catalyst brief
/thesis\\_check [ticker] — Bull/bear thesis check
/idea\\_generation [name] — Mandate-aware stock ideas
/morning\\_note [ticker] — Morning briefing for a name

*V3 — Portfolio Intelligence*
/portfolio\\_scenario [name] — Portfolio scenario analysis

/help — show this message
"""
```

- [ ] **Step 2: Register 6 new CommandHandlers in build_application**

In `build_application`, add after the existing V2 handlers:

```python
    # V3 — Equity Research Plugin
    app.add_handler(CommandHandler("earnings_deep_dive", _make_command_handler("earnings-deep-dive", router, sheets_service)))
    app.add_handler(CommandHandler("stock_catalyst",     _make_command_handler("stock-catalyst",     router, sheets_service)))
    app.add_handler(CommandHandler("thesis_check",       _make_command_handler("thesis-check",       router, sheets_service)))
    app.add_handler(CommandHandler("idea_generation",    _make_command_handler("idea-generation",    router, sheets_service)))
    app.add_handler(CommandHandler("morning_note",       _make_command_handler("morning-note",       router, sheets_service)))
    # V3 — Wealth Management Plugin
    app.add_handler(CommandHandler("portfolio_scenario", _make_command_handler("portfolio-scenario", router, sheets_service)))
```

- [ ] **Step 3: Verify no import errors**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "from bot.telegram_bot import build_application; print('telegram_bot OK')"
```
Expected: `telegram_bot OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add bot/telegram_bot.py
git commit -m "feat: register 6 V3 Telegram commands and update /help text"
```

---

## Task 8: Add V3 NL Intents to ChatRouter

**Files:**
- Modify: `services/chat_router.py`

- [ ] **Step 1: Add V3 intents to the INTENTS dict**

In `services/chat_router.py`, add to the `INTENTS` dict:

```python
    "earnings_deep_dive": [
        "earnings", "results", "quarterly results", "earnings deep dive",
        "how did", "how did it do", "beat", "miss", "guidance",
    ],
    "stock_catalyst": [
        "catalyst", "catalysts", "what's driving", "whats driving",
        "what could move", "near term", "upcoming", "what to watch",
    ],
    "thesis_check": [
        "thesis", "bull case", "bear case", "investment case",
        "why own", "why hold", "conviction", "view on",
    ],
    "idea_generation": [
        "ideas for", "what should i look at", "stock ideas",
        "what fits", "ideas for", "suggest something for",
        "what would work for", "any ideas",
    ],
    "morning_note": [
        "morning note", "morning brief", "morning update",
        "what to know about", "quick brief on", "brief on",
    ],
    "portfolio_scenario": [
        "scenario", "portfolio scenario", "stress test",
        "what if", "downside scenario", "risk scenario",
        "portfolio risk", "what happens if",
    ],
```

- [ ] **Step 2: Add V3 entries to HELP_TEXT in chat_router.py**

Replace the `HELP_TEXT` constant in `chat_router.py` with:

```python
HELP_TEXT = (
    "*Aureus RM Copilot* — what I can do:\n\n"
    "*V2 Client & Portfolio:*\n"
    "- *Client Review* — `review John Tan`\n"
    "- *Meeting Pack* — `meeting pack for John Tan`\n"
    "- *Next Best Actions* — `what should I do for John Tan`\n"
    "- *Portfolio Fit* — `does DBS fit John Tan`\n\n"
    "*V3 Equity Research:*\n"
    "- *Earnings* — `how did NVDA do this quarter`\n"
    "- *Catalyst* — `what's driving TSM`\n"
    "- *Thesis* — `bull case for AAPL`\n"
    "- *Ideas* — `any ideas for John Tan`\n"
    "- *Morning Note* — `morning brief on DBS`\n"
    "- *Portfolio Scenario* — `stress test John Tan's portfolio`\n\n"
    "Or use slash commands — type /help."
)
```

- [ ] **Step 3: Update intent → command mapping in _build_resolution**

In `_build_resolution`, update `command_map` to include V3 intents:

```python
    command_map = {
        # V2
        "client_review":    "client-review",
        "meeting_pack":     "meeting-pack",
        "next_best_action": "next-best-action",
        "portfolio_fit":    "portfolio-fit",
        # V3
        "earnings_deep_dive": "earnings-deep-dive",
        "stock_catalyst":     "stock-catalyst",
        "thesis_check":       "thesis-check",
        "idea_generation":    "idea-generation",
        "morning_note":       "morning-note",
        "portfolio_scenario": "portfolio-scenario",
    }
```

- [ ] **Step 4: Update resolve() to handle ticker-first vs client-first commands**

In `resolve()`, after detecting intent, add ticker extraction for the equity research commands that take a ticker:

```python
    # Ticker-primary commands: extract ticker as the primary arg
    TICKER_COMMANDS = {"earnings_deep_dive", "stock_catalyst", "thesis_check", "morning_note"}
    # Client-primary commands (V3): same as V2 — extract client name
    CLIENT_COMMANDS = {"idea_generation", "portfolio_scenario"}

    state.intent = intent
    state.waiting_for = None

    if intent in TICKER_COMMANDS:
        state.ticker = _extract_ticker(stripped)
        state.client_name = None
        if not state.ticker:
            state.waiting_for = "ticker"
            prompts = {
                "earnings_deep_dive": "Which ticker would you like an earnings deep dive on?",
                "stock_catalyst":     "Which ticker are you looking at for catalysts?",
                "thesis_check":       "Which ticker should I check the thesis for?",
                "morning_note":       "Which ticker or sector would you like a morning note on?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which ticker?"))
    elif intent in CLIENT_COMMANDS:
        state.ticker = None
        state.client_name = _extract_client_name(stripped, intent)
        if not state.client_name:
            state.waiting_for = "client_name"
            prompts = {
                "idea_generation":   "Which client should I generate ideas for?",
                "portfolio_scenario": "Which client's portfolio should I run scenarios on?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which client?"))
    else:
        # V2 intents — unchanged path
        state.client_name = _extract_client_name(stripped, intent)
        state.ticker = _extract_ticker(stripped) if intent == "portfolio_fit" else None
        if not state.client_name:
            state.waiting_for = "client_name"
            prompts = {
                "client_review":     "Sure — which client would you like a review for?",
                "meeting_pack":      "Happy to help prep. Which client is the meeting for?",
                "next_best_action":  "Which client should I suggest next actions for?",
                "portfolio_fit":     "Which client are you assessing?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which client?"))
        if intent == "portfolio_fit" and not state.ticker:
            state.waiting_for = "ticker"
            return ChatResolution(
                reply=f"Got it — *{state.client_name}*. Which ticker are you looking at?"
            )
```

- [ ] **Step 5: Update _build_resolution to handle ticker-primary commands**

In `_build_resolution`, update to handle V3 ticker-primary intents:

```python
def _build_resolution(state: ConversationState, chat_id: str) -> ChatResolution:
    """Map resolved intent + args to a command_router command."""
    command_map = {
        "client_review":      "client-review",
        "meeting_pack":       "meeting-pack",
        "next_best_action":   "next-best-action",
        "portfolio_fit":      "portfolio-fit",
        "earnings_deep_dive": "earnings-deep-dive",
        "stock_catalyst":     "stock-catalyst",
        "thesis_check":       "thesis-check",
        "idea_generation":    "idea-generation",
        "morning_note":       "morning-note",
        "portfolio_scenario": "portfolio-scenario",
    }
    command = command_map[state.intent]

    TICKER_COMMANDS = {"earnings_deep_dive", "stock_catalyst", "thesis_check", "morning_note"}
    if state.intent in TICKER_COMMANDS:
        args = [state.ticker] if state.ticker else []
    else:
        args = state.client_name.split() if state.client_name else []
        if state.intent == "portfolio_fit" and state.ticker:
            args = args + [state.ticker]

    logger.info(
        "ChatRouter resolved | chat_id=%s intent=%s client=%s ticker=%s",
        chat_id, state.intent, state.client_name, state.ticker,
    )

    state.reset()
    return ChatResolution(command=command, args=args)
```

- [ ] **Step 6: Smoke test chat_router**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
from services.chat_router import resolve

# Ticker-primary
r = resolve('test_chat', 'what is the earnings story for NVDA')
print('earnings intent:', r.command, r.args)

r2 = resolve('test_chat2', 'bull case for AAPL')
print('thesis intent:', r2.command, r2.args)

r3 = resolve('test_chat3', 'any ideas for John Tan')
print('idea intent:', r3.command, r3.args)

# V2 still works
r4 = resolve('test_chat4', 'review John Tan')
print('client_review V2:', r4.command, r4.args)
print('ALL OK')
"
```
Expected: All 4 resolved with correct command + args. Ends with `ALL OK`.

- [ ] **Step 7: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add services/chat_router.py
git commit -m "feat: add V3 NL intents and arg extraction to ChatRouter"
```

---

## Task 9: Update app.py

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Instantiate new services and pass to CommandRouter**

In `app.py`, after the `from services.command_router import CommandRouter` import, add:

```python
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
```

In `main()`, after `client_service = ClientService(sheets=sheets, use_mock=use_mock)`, add:

```python
    # V3 — Core Financial Analysis Layer + Equity Research Plugin
    financial_analysis = FinancialAnalysisService()
    equity_research = EquityResearchService(financial_analysis=financial_analysis)
    logger.info("V3 services initialised | mock_universe=%s", financial_analysis.get_stock_universe())
```

Update `CommandRouter` instantiation:

```python
    router = CommandRouter(
        client_service=client_service,
        claude_service=claude_service,
        sheets_service=sheets,
        financial_analysis=financial_analysis,
        equity_research=equity_research,
    )
```

- [ ] **Step 2: Verify app.py imports cleanly**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
import app
print('app.py imports OK')
"
```
Expected: `app.py imports OK` (no errors).

- [ ] **Step 3: Commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add app.py
git commit -m "feat: wire FinancialAnalysisService and EquityResearchService into app startup"
```

---

## Task 10: Create Skills and Docs Files

**Files:**
- Create: `skills/financial-analysis-core.md`
- Create: `skills/earnings-analysis-framework.md`
- Create: `skills/catalyst-analysis-framework.md`
- Create: `skills/thesis-analysis-framework.md`
- Create: `skills/idea-generation-framework.md`
- Create: `skills/morning-note-framework.md`
- Create: `skills/portfolio-scenario-thinking.md`
- Create: `docs/core-financial-analysis-layer.md`
- Create: `docs/equity-research-plugin.md`
- Create: `docs/portfolio-intelligence.md`

- [ ] **Step 1: Create skills/financial-analysis-core.md**

```markdown
# Financial Analysis Core — Skill Reference

## Purpose
This skill governs how Aureus reasons about stocks and financial data. It applies to all commands that involve stock analysis, regardless of whether the context is equity research or wealth management.

## Core Reasoning Principles

- **Facts before interpretation.** State what the data shows before drawing conclusions. Label the distinction clearly.
- **No fabricated data.** If a data field is empty or unavailable, say so. Do not invent estimates.
- **Mock data labelling.** All outputs from Phase 1 mock data must carry the note: *[MOCK / NOT REAL-TIME — for framework and internal use only]*.
- **Valuation is context-dependent.** A PE of 28x means something different for a high-growth tech company than for a bank. Always contextualise multiples against sector and growth profile.
- **Thesis integrity.** Every stock view must have a bull case and bear case. Conviction without a bear case is incomplete.

## Output Rules
- Max 3 bullets per section
- No tables in Telegram output
- Separate facts from RM framing
- Disclaimer on every output: *For internal RM use only. Not investment advice.*

## Future Connector Insertion Point
When live market and news connectors are available (Phase 2+), they plug in at `FinancialAnalysisService` in `services/financial_analysis_service.py`. Pass a live `connector` instance — callers do not change.
```

- [ ] **Step 2: Create skills/earnings-analysis-framework.md**

```markdown
# Earnings Analysis Framework — Skill Reference

## Purpose
Guide Aureus responses for `/earnings_deep_dive`. Ensures earnings outputs are factual, RM-ready, and compliance-safe.

## How to Reason About Earnings

1. **Headline first.** Revenue and EPS vs. consensus — did the company beat, miss, or come in line? State the fact before the interpretation.
2. **What changed vs. prior narrative.** A beat that comes with guidance cuts is not a clean beat. A miss with raised guidance may be more positive than it looks. Always compare to what was expected, not just to prior actuals.
3. **Management tone.** Cautious, Neutral, or Confident — based on language used, not outcome. A confident tone on a miss is informative. A cautious tone on a beat is also informative.
4. **Forward read-through.** What do the results say about the next quarter or the full year? Do not present guidance as certainty — attribute it to management.

## RM Output Rules
- Beat/miss on revenue AND EPS (both required)
- Guidance direction: Raised / Lowered / Maintained / Initiated
- One-sentence management characterisation
- RM framing: what clients who hold this stock are likely to ask

## What Not To Do
- Do not present guidance as a forecast
- Do not invent consensus estimates if unavailable
- Do not characterise results as "good" or "bad" without citing the data
```

- [ ] **Step 3: Create skills/catalyst-analysis-framework.md**

```markdown
# Catalyst Analysis Framework — Skill Reference

## Purpose
Guide Aureus responses for `/stock_catalyst`. Ensures catalyst briefs are specific, near-term, and useful for RM conversations.

## What Makes a Good Catalyst

A catalyst is a specific, near-term event or development that could move the stock meaningfully. Generic statements ("strong earnings outlook") are not catalysts. Specific events ("Q4 earnings release expected to show first positive free cash flow") are.

## Catalyst Hierarchy (by RM usefulness)
1. **Earnings events** — next scheduled earnings, pre-announcements
2. **Product/regulatory milestones** — launches, approvals, rulings
3. **Capital allocation events** — dividends, buybacks, M&A
4. **Macro or sector turning points** — rate changes, commodity moves, policy shifts

## RM Output Rules
- 2–3 catalysts maximum per brief
- State the catalyst, the expected timing if known, and the directional implication
- Separate catalysts (positive) from risks (negative)
- RM framing: how to introduce the catalyst conversation without giving a price target

## What Not To Do
- Do not list permanent structural advantages as near-term catalysts
- Do not use language like "will drive the stock higher"
- Do not present catalysts as investment recommendations
```

- [ ] **Step 4: Create skills/thesis-analysis-framework.md**

```markdown
# Thesis Analysis Framework — Skill Reference

## Purpose
Guide Aureus responses for `/thesis_check`. Ensures thesis outputs present a balanced, honest bull/bear framing for RM use.

## Thesis Structure

Every thesis has three parts:
1. **Bull case** — why the stock could outperform. Must be specific to this company (not generic sector commentary).
2. **Bear case** — why the stock could underperform or disappoint. Must be specific and honest — do not soften the bear case.
3. **Conviction** — High / Medium / Low. Reflects the strength of the bull case relative to the bear case, not just optimism.

## Conviction Definitions
- **High** — Bull case is well-supported by data; bear case is identifiable but manageable or well-priced in
- **Medium** — Balanced bull and bear cases; outcome is genuinely uncertain
- **Low** — Bear case is at least as strong as the bull case; not the right time to raise the name with most clients

## RM Output Rules
- Bull case: one sentence, specific
- Bear case: one sentence, honest — do not bury it
- Conviction level always stated
- RM framing: when to raise the name (conviction High + mandate fit) and when to hold back (bear case live)

## What Not To Do
- Do not omit the bear case
- Do not present a bull case so qualified it says nothing
- Do not use conviction language that implies a price target or return forecast
```

- [ ] **Step 5: Create skills/idea-generation-framework.md**

```markdown
# Idea Generation Framework — Skill Reference

## Purpose
Guide Aureus responses for `/idea_generation`. Ensures ideas are mandate-aware, not generic stock picks.

## How Idea Generation Works

1. **Start with the mandate.** The client's risk profile, investment objective, and any sector restrictions define the filter. A High conviction idea that violates the mandate is not an idea — it is a risk.
2. **Screen by conviction.** High conviction ideas surface first. Medium conviction ideas are included if they fit the mandate. Low conviction ideas are not surfaced unless the universe is otherwise empty.
3. **One rationale per idea.** Each idea needs one sentence explaining why it fits this specific client — not a generic description of the stock.

## Idea Output Rules
- Max 3 ideas per output
- Each idea: ticker, sector, conviction level, one-line rationale specific to this client
- Always note: "Validate against suitability before raising. Use /thesis_check [ticker] for detail."
- RM framing: how to open the idea conversation (not "I recommend" — "I've been looking at...")

## What Not To Do
- Do not surface ideas that violate the client's mandate
- Do not present ideas as recommendations
- Do not list more than 3 ideas — quality over quantity
```

- [ ] **Step 6: Create skills/morning-note-framework.md**

```markdown
# Morning Note Framework — Skill Reference

## Purpose
Guide Aureus responses for `/morning_note`. Produces a concise, actionable morning brief for an RM going into client conversations.

## Morning Note Structure

A morning note is not a report. It is a 60-second prep that answers: *What do I need to know about this name going into today?*

1. **What it is** — one line on the company and where it sits in the current market narrative
2. **What to know today** — 2–3 things relevant to RM conversations this morning (catalysts, earnings, sector moves, news)
3. **What could move against it** — 1–2 near-term risks to be aware of
4. **How to surface it** — one sentence on the right way to raise this name in a morning touchpoint

## RM Output Rules
- Snapshot: name, sector, geography (one line)
- Key observations: 2–3 bullets, morning-relevant
- Risks: 1–2 bullets
- RM framing: one sentence — natural, not scripted

## What Not To Do
- Do not write a full research report
- Do not cite stale data without labelling it
- Do not use language that implies a recommendation
```

- [ ] **Step 7: Create skills/portfolio-scenario-thinking.md**

```markdown
# Portfolio Scenario Thinking — Skill Reference

## Purpose
Guide Aureus responses for `/portfolio_scenario`. Helps RMs think through portfolio risk before client meetings — not as a prediction, but as a preparedness exercise.

## Scenario Thinking Principles

1. **Scenarios are not forecasts.** Present scenarios as possibilities, not predictions. Never imply one scenario is more likely unless the data supports it.
2. **Client context first.** The client's mandate and risk profile determine which scenarios matter most. A rate-cut scenario means something different to a conservative income client vs. a growth client.
3. **Actionable framing.** A scenario is only useful if the RM can do something with it. Frame each scenario as: *if this happens, what should the RM have ready?*

## Portfolio Scenario Output Rules
- Cover the client's top holdings (max 5)
- Per holding: one key scenario + impact + one-line note
- Portfolio-level observation: which holdings are correlated to the same scenario risk
- RM framing: how to raise scenario thinking with the client without alarming them

## How to Frame Scenario Conversations with Clients
- "One thing I've been thinking about for your portfolio..."
- "I want to make sure we're prepared if..."
- Never: "Your portfolio is at risk of..."
- Never: "You should sell X because of scenario Y"

## What Not To Do
- Do not present scenarios as predictions or price targets
- Do not omit the client's mandate context when assessing scenario impact
- Do not fabricate scenario data — label all Phase 1 scenarios as mock/framework-based
```

- [ ] **Step 8: Create docs/core-financial-analysis-layer.md**

```markdown
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
```

- [ ] **Step 9: Create docs/equity-research-plugin.md**

```markdown
# Equity Research Plugin

## Overview

`services/equity_research_service.py` is a thin orchestration layer over the Core Financial Analysis Layer. It composes Core context builders into command-ready payloads for equity research commands. It does not duplicate stock logic from Core.

## Commands

| Command | Args | Context builder | Core methods used |
|---|---|---|---|
| `/earnings_deep_dive` | ticker | `build_earnings_context` | `build_financial_snapshot_context` + `build_catalyst_context` |
| `/stock_catalyst` | ticker | Core direct | `build_catalyst_context` |
| `/thesis_check` | ticker | Core direct | `build_thesis_context` |
| `/idea_generation` | client name | `build_idea_context` | `get_stock_universe` + `build_thesis_context` per ticker |
| `/morning_note` | ticker or sector | `build_morning_note_context` | `build_financial_snapshot_context` + `build_catalyst_context` + `build_thesis_context` |

## Design Decisions

- `/stock_catalyst` and `/thesis_check` are routed directly through Core in `command_router.py` — no plugin wrapper is needed for single-method commands.
- `/idea_generation` screens the full mock universe against the client's mandate and returns the top 3 High→Medium→Low conviction ideas.
- All outputs carry `is_mock: True` and `source_label: "MOCK / NOT REAL-TIME"` in Phase 1.

## Skills

- `skills/earnings-analysis-framework.md`
- `skills/catalyst-analysis-framework.md`
- `skills/thesis-analysis-framework.md`
- `skills/idea-generation-framework.md`
- `skills/morning-note-framework.md`
```

- [ ] **Step 10: Create docs/portfolio-intelligence.md**

```markdown
# Portfolio Intelligence — Wealth Management Plugin

## Overview

The Wealth Management Plugin extends the existing V2 client and portfolio commands with portfolio scenario intelligence. It uses `ClientService` (Google Sheets) as the client source of truth and `FinancialAnalysisService` (Core layer) for scenario framing.

## Commands

| Command | Data sources | Description |
|---|---|---|
| `/client_review` | ClientService | Full client review (V2, unchanged) |
| `/meeting_pack` | ClientService | Meeting prep pack (V2, unchanged) |
| `/next_best_action` | ClientService | Next best actions (V2, unchanged) |
| `/portfolio_fit` | ClientService | Portfolio fit check (V2, unchanged) |
| `/portfolio_scenario` | ClientService + FinancialAnalysisService | Portfolio scenario analysis (V3 new) |

## Portfolio Scenario Design

`/portfolio_scenario` pulls the client's top holdings from `ClientService`, then calls `FinancialAnalysisService.build_scenario_context()` for each held ticker. The result is a scenario map across the portfolio — showing which holdings are exposed to which stress scenarios and how.

For holdings not in the mock universe, `FinancialAnalysisService.get_stock()` returns a labelled stub — the command still runs, it just notes the data gap for that ticker.

## Data Sources

- **Client data:** Google Sheets via `SheetsService` + `ClientService`. Falls back to `MOCK_CUSTOMER` / `MOCK_HOLDINGS` in mock mode.
- **Stock scenario data:** `MOCK_STOCKS` in Phase 1. Live connectors in Phase 2+.

## Skills

- `skills/portfolio-scenario-thinking.md`

## Future Additions

- Scenario-aware enrichment in `/client_review` and `/meeting_pack` prompts (light touch, no data flow change)
- Live scenario data from market risk connector (Phase 2)
```

- [ ] **Step 11: Verify all new files exist**

```bash
ls /Users/edwardchiang/aureus-rm/skills/
ls /Users/edwardchiang/aureus-rm/docs/
```
Expected: All 7 new skill files and 3 new doc files visible.

- [ ] **Step 12: Commit all docs and skills**

```bash
cd /Users/edwardchiang/aureus-rm && git add skills/ docs/
git commit -m "docs: add V3 skills and architecture docs (Core, Equity Research, Portfolio Intelligence)"
```

---

## Task 11: Final Integration Check

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/edwardchiang/aureus-rm && python -m pytest tests/ -v
```
Expected: All tests PASS. No failures.

- [ ] **Step 2: Full end-to-end smoke test**

```bash
cd /Users/edwardchiang/aureus-rm && python -c "
import asyncio
from services.client_service import ClientService
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
from services.command_router import CommandRouter

fa = FinancialAnalysisService()
er = EquityResearchService(financial_analysis=fa)
cs = ClientService(sheets=None, use_mock=True)
router = CommandRouter(client_service=cs, financial_analysis=fa, equity_research=er)

async def test_all():
    commands = [
        ('client-review', ['John', 'Tan']),
        ('portfolio-fit', ['John', 'Tan', 'D05.SI']),
        ('meeting-pack', ['John', 'Tan']),
        ('next-best-action', ['John', 'Tan']),
        ('earnings-deep-dive', ['NVDA']),
        ('stock-catalyst', ['TSM']),
        ('thesis-check', ['AAPL']),
        ('idea-generation', ['John', 'Tan']),
        ('morning-note', ['DBS']),
        ('portfolio-scenario', ['John', 'Tan']),
    ]
    for cmd, args in commands:
        r = await router.route(cmd, args)
        assert r and len(r) > 50, f'{cmd} returned empty or too short'
        print(f'✓ /{cmd}')
    print('ALL 10 COMMANDS PASS')

asyncio.run(test_all())
"
```
Expected: 10 checkmarks and `ALL 10 COMMANDS PASS`.

- [ ] **Step 3: Final commit**

```bash
cd /Users/edwardchiang/aureus-rm && git add -A
git commit -m "feat: V3 equity research — complete 3-layer architecture (Core + Equity Plugin + WM Plugin)"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|---|---|
| `services/financial_analysis_service.py` with `build_financial_snapshot_context` + 7 methods | Task 2 |
| `services/equity_research_service.py` thin orchestration | Task 3 |
| MOCK_STOCKS for DBS, UOB, AAPL, NVDA, TSM with `is_mock`, `data_freshness`, `source_label` | Task 1 |
| 6 V3 commands registered in Telegram | Task 7 |
| 6 V3 NL intents in chat_router | Task 8 |
| 6 V3 Claude prompts | Task 4 |
| 6 V3 template fallbacks | Task 5 |
| 6 V3 handlers in command_router | Task 6 |
| V2 commands preserved unchanged | Task 6 (no-touch), Task 11 (verified) |
| `skills/financial-analysis-core.md` | Task 10 |
| `skills/earnings-analysis-framework.md` | Task 10 |
| `skills/catalyst-analysis-framework.md` | Task 10 |
| `skills/thesis-analysis-framework.md` | Task 10 |
| `skills/idea-generation-framework.md` | Task 10 |
| `skills/morning-note-framework.md` | Task 10 |
| `skills/portfolio-scenario-thinking.md` | Task 10 |
| `docs/core-financial-analysis-layer.md` | Task 10 |
| `docs/equity-research-plugin.md` | Task 10 |
| `docs/portfolio-intelligence.md` | Task 10 |
| `app.py` wired with new services | Task 9 |
| Fallback mode preserved | Task 5 (formatters), Task 6 (handler guards) |
| Future-readiness (connector kwarg) | Task 2 (FinancialAnalysisService.__init__) |
| Telegram UI preserved | Task 7 |
| Google Sheets as client source of truth | Task 6 (ClientService unchanged) |

**No gaps found.**

**Type/name consistency:** All method names (`build_earnings_context`, `build_catalyst_context`, `build_thesis_context`, `build_idea_context`, `build_morning_note_context`, `build_portfolio_scenario_context`) are consistent across Tasks 2, 3, 4, 5, 6. Command strings ("earnings-deep-dive", "stock-catalyst", etc.) match across route(), COMMAND_PROMPTS, formatters dict, and Telegram handler registration.
