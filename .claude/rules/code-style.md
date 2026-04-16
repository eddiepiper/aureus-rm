# Code Style — Aureus RM Copilot

## Language and Runtime

- Python 3.11+
- No frameworks beyond what's in `requirements.txt` — keep dependencies minimal
- All entry points use `if __name__ == "__main__"` guards

## Module Structure

- `services/` — one class per service, constructor takes config and external dependencies
- `bot/` — Telegram handler wiring only; no business logic in handlers
- `hooks/` — Python MCP lifecycle hooks; each hook is a standalone module with a single `run()` entry point
- `schemas/` — JSON Schema only; no Python models in this directory
- `tests/` — mirror the structure of the module under test; one test file per service

## Naming

- `snake_case` for all Python identifiers
- Service classes: `XxxService` (e.g., `SheetsService`, `ClientService`)
- Agent classes: `XxxAgent` (e.g., `PortfolioCounsellorAgent`, `EquityAnalystAgent`)
- Hook files: `pre_response_guardrail.py`, `crm_logger.py` — verb + noun, no abbreviations

## Key Patterns

- Services accept all external dependencies via constructor — do not import globals in service bodies
- Use `pydantic` models for all structured data shapes that cross service boundaries
- Config is loaded once at startup (`services/config.py`) — do not re-read `.env` in service code
- Errors: raise typed exceptions, catch at the orchestrator level, never silently swallow

## Adding Code

When adding a new command:
1. Create `.claude/commands/[name].md` with the prompt template
2. Add any new skills to `.claude/skills/`
3. Document the command in `CLAUDE.md` under the Commands table
4. Test with mock server before live connector testing

When adding a new service:
1. Add to `services/[name]_service.py`
2. Wire into `app.py` startup sequence
3. Add unit tests to `tests/test_[name]_service.py`

## Tests

- Use `pytest` — no unittest
- Mock external calls (Sheets, Telegram, MCP tools) at the service boundary
- Every hook must have a test that verifies the trigger condition and the action taken
- Target: all new code covered; existing coverage in `tests/` is the baseline
