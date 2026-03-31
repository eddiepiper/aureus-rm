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
