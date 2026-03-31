# Aureus V3 — Equity Research Architecture Design
*Date: 2026-03-30 | Branch: v3-equity-research-full*

---

## 1. Overview

V3 introduces a 3-layer architecture that separates shared financial reasoning (Core), equity research workflows (Equity Research Plugin), and RM/client workflows (Wealth Management Plugin). All V2 commands are preserved unchanged. The new layer structure eliminates duplication and provides a clean insertion point for future live market and news connectors.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram UI Layer                     │
│         telegram_bot.py  ·  chat_router.py              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Command Router  (command_router.py)         │
│         Claude Service  ·  Response Formatter            │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
┌──────────────▼──────┐  ┌────────────▼──────────────────┐
│  Equity Research    │  │  Wealth Management Plugin      │
│  Plugin             │  │  client_service.py (unchanged) │
│  equity_research_   │  │  + portfolio_scenario handler  │
│  service.py         │  │                                │
└──────────────┬──────┘  └────────────┬──────────────────┘
               │                      │
┌──────────────▼──────────────────────▼──────────────────┐
│          Core Financial Analysis Layer                   │
│          financial_analysis_service.py                   │
│  snapshot · catalyst · thesis · valuation ·             │
│  scenario · compare · financial_snapshot                │
└─────────────────────────┬───────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  MOCK_STOCKS (Phase 1)│
              │  DBS · UOB · AAPL ·  │
              │  NVDA · TSM           │
              │                       │
              │  → live connectors    │
              │    (Phase 2+)         │
              └───────────────────────┘
```

**Data sources:**
- Client data: Google Sheets (unchanged, via `SheetsService` + `ClientService`)
- Stock data: `MOCK_STOCKS` in `mock_data.py` (Phase 1); live MCP connectors (Phase 2+)
- UI: Telegram (unchanged)

---

## 3. Core Financial Analysis Layer

**File:** `services/financial_analysis_service.py`

The shared foundation for all stock and portfolio reasoning. No command-specific logic lives here. Both the Equity Research Plugin and the Wealth Management Plugin depend on this layer. Future live market and news connectors will be wired in here — callers do not change.

### Methods

| Method | Purpose |
|---|---|
| `get_stock(ticker)` | Return raw mock record; return labelled stub if ticker unknown |
| `get_stock_universe()` | Return list of all available tickers |
| `build_financial_snapshot_context(ticker)` | Clean stock snapshot used by earnings_deep_dive, thesis_check, morning_note |
| `build_catalyst_context(ticker)` | Catalysts, risks, conviction level |
| `build_thesis_context(ticker)` | Bull case, bear case, thesis quality flag |
| `build_valuation_context(ticker)` | Key financials (no real-time prices) |
| `build_scenario_context(ticker)` | 2 stress scenarios + impact framing |
| `build_compare_context(t1, t2)` | Side-by-side snapshot for two tickers |

### Future-readiness

Each method accepts an optional `connector=None` kwarg. In Phase 1 this defaults to mock. In Phase 2, pass a live MCP connector instance to replace mock lookups without changing callers or command logic.

### Mock data contract

All outputs carry:
```python
{
    "is_mock": True,
    "data_freshness": "framework-based",
    "source_label": "MOCK / NOT REAL-TIME",
    ...
}
```

---

## 4. Equity Research Plugin

**File:** `services/equity_research_service.py`

Thin orchestration layer. Composes Core context builders into command-ready payloads. Does not duplicate stock logic from Core.

### Methods

| Method | Command | Core methods used |
|---|---|---|
| `build_earnings_context(ticker)` | `/earnings_deep_dive` | `build_financial_snapshot_context` + `build_catalyst_context` |
| `build_morning_note_context(input)` | `/morning_note` | `build_financial_snapshot_context` + `build_catalyst_context` + `build_thesis_context` |
| `build_idea_context(client_ctx)` | `/idea_generation` | `get_stock_universe()` + `build_thesis_context` per ticker screened against client mandate |

`/stock_catalyst` and `/thesis_check` are routed directly through Core in `command_router.py` — no plugin wrapper needed.

### Commands

| Command | Args | Handler |
|---|---|---|
| `/earnings_deep_dive [ticker]` | ticker | `EquityResearchService.build_earnings_context` |
| `/stock_catalyst [ticker]` | ticker | `FinancialAnalysisService.build_catalyst_context` directly |
| `/thesis_check [ticker]` | ticker | `FinancialAnalysisService.build_thesis_context` directly |
| `/idea_generation [client_name]` | client name | `EquityResearchService.build_idea_context` |
| `/morning_note [ticker or sector]` | ticker or sector | `EquityResearchService.build_morning_note_context` |

---

## 5. Wealth Management Plugin

**Data layer:** `services/client_service.py` (unchanged — Google Sheets source of truth)

### Commands

| Command | Data sources | Change |
|---|---|---|
| `/client_review` | ClientService | None — V2 unchanged |
| `/meeting_pack` | ClientService | None — V2 unchanged |
| `/next_best_action` | ClientService | None — V2 unchanged |
| `/portfolio_fit` | ClientService | None — V2 unchanged |
| `/portfolio_scenario [client_name]` | ClientService + FinancialAnalysisService | New |

`/portfolio_scenario` uses client holdings from `ClientService` and scenario framing from `FinancialAnalysisService.build_scenario_context()` for each held ticker.

`/client_review` and `/meeting_pack` may optionally surface light scenario-aware observations via Claude prompt enrichment — but the data flow and handlers are not rewritten.

---

## 6. New Commands — Full List

**V3 (new):**
- `/earnings_deep_dive [ticker]`
- `/stock_catalyst [ticker]`
- `/thesis_check [ticker]`
- `/idea_generation [client_name]`
- `/morning_note [ticker or sector]`
- `/portfolio_scenario [client_name]`

**V2 (preserved unchanged):**
- `/client_review [client_name]`
- `/meeting_pack [client_name]`
- `/next_best_action [client_name]`
- `/portfolio_fit [client_name] [ticker]`

---

## 7. Output Format (all V3 commands)

Consistent Telegram-friendly 4-section format:

```
*[Command Title] — [TICKER / CLIENT]*
⚠️ MOCK DATA — framework-based, not real-time

*Snapshot* — 1–2 lines
*Key Observations* — max 3 bullets
*Key Risks / Watchouts* — max 2 bullets
*RM Framing / Suggested Next Action* — 1–2 lines

_For internal RM use only. Not investment advice._
```

Rules:
- Max 3 bullets per section
- No markdown tables
- No fabricated prices or real-time data
- All stock context labelled as mock/framework-based

---

## 8. Mock Stock Universe

**File:** `services/mock_data.py` — add `MOCK_STOCKS` dict.

Tickers: `DBS`, `UOB`, `AAPL`, `NVDA`, `TSM`

Each record shape:
```python
{
    "ticker": str,
    "is_mock": True,
    "data_freshness": "framework-based",
    "source_label": "MOCK / NOT REAL-TIME",
    "snapshot": {
        "name": str,
        "sector": str,
        "geography": str,
        "market_cap_band": str,        # e.g. "Large Cap"
        "description": str,            # 1–2 sentences
    },
    "financials": {
        "revenue_ttm": str,
        "eps_ttm": str,
        "pe_ratio": str,
        "pb_ratio": str,
        "roe_pct": str,
        "div_yield_pct": str,
    },
    "earnings": {
        "quarter": str,
        "revenue_actual": str,
        "revenue_est": str,
        "eps_actual": str,
        "eps_est": str,
        "beat_miss": str,              # "Beat" | "Miss" | "In-line"
        "guidance_direction": str,     # "Raised" | "Lowered" | "Maintained"
        "mgmt_tone": str,              # "Cautious" | "Neutral" | "Confident"
    },
    "catalysts": [str, str],           # 2–3 near-term factors
    "risks": [str, str],               # 2–3 key risks
    "thesis": {
        "bull_case": str,
        "bear_case": str,
        "conviction": str,             # "High" | "Medium" | "Low"
    },
    "scenarios": [
        {"name": str, "impact": str, "note": str},  # 2 stress scenarios
    ],
}
```

---

## 9. New Files

| File | Layer | Purpose |
|---|---|---|
| `services/financial_analysis_service.py` | Core | Shared financial context builders |
| `services/equity_research_service.py` | Equity Research | Thin orchestration over Core |
| `skills/financial-analysis-core.md` | Core | Reasoning framework for stock analysis |
| `skills/earnings-analysis-framework.md` | Equity Research | How to reason about earnings results |
| `skills/catalyst-analysis-framework.md` | Equity Research | How to identify and frame catalysts |
| `skills/thesis-analysis-framework.md` | Equity Research | Bull/bear thesis construction |
| `skills/idea-generation-framework.md` | Equity Research | Mandate-aware idea screening |
| `skills/morning-note-framework.md` | Equity Research | Morning note structure and framing |
| `skills/portfolio-scenario-thinking.md` | Wealth Management | Portfolio scenario reasoning |
| `docs/core-financial-analysis-layer.md` | Core | Architecture doc for Core layer |
| `docs/equity-research-plugin.md` | Equity Research | Architecture doc for Equity plugin |
| `docs/portfolio-intelligence.md` | Wealth Management | Architecture doc for WM plugin |

---

## 10. Modified Files

| File | Change |
|---|---|
| `services/mock_data.py` | Add `MOCK_STOCKS` (5 tickers) |
| `services/command_router.py` | Inject `FinancialAnalysisService` + `EquityResearchService`; add 6 handlers |
| `services/claude_service.py` | Add 6 command prompts (same 4-section format) |
| `services/response_formatter.py` | Add 6 template fallbacks |
| `bot/telegram_bot.py` | Register 6 slash commands; update `/help` text |
| `services/chat_router.py` | Add NL intents + arg extraction for 6 commands |
| `app.py` | Instantiate `FinancialAnalysisService` + `EquityResearchService`; pass to router |

---

## 11. Constraints

- Do not touch `main` branch
- All changes on `v3-equity-research-full`
- V2 command handlers must not be modified
- No real-time data — all stock data is mock/framework-based
- Fallback mode (no Claude API key) must produce valid template output for all 6 new commands
- Telegram 4096 char limit enforced via existing `_split_message`
