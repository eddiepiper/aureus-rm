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
