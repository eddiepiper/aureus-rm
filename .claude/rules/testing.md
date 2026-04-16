# Testing Rules — Aureus RM Copilot

## Test Runner

```bash
python -m pytest tests/ -q          # full suite
python -m pytest tests/ -v          # verbose
python -m pytest tests/test_X.py -v # single file
```

## Test Structure

```
tests/
├── test_financial_analysis_service.py
├── test_equity_research_service.py
├── test_mock_data.py
└── test_guardrail.py               # guardrail rules regression tests
```

One test file per service module. Mirror the module structure.

## What to Test

| Concern | Test Approach |
|---------|--------------|
| Service logic | Unit test with mocked external calls |
| Guardrail rules | Regression tests for every prohibited pattern in `hooks/pre_response_guardrail.py` |
| Hook behavior | Test trigger condition (input that fires) + action taken (output/side effect) |
| MCP tool responses | Test against fixtures in `examples/sample-outputs.md` |
| Schema validation | Test output structures against JSON schemas in `schemas/` |

## Mocking

- Mock all external calls (Google Sheets, Telegram API, MCP tool responses) at the service interface
- Use `unittest.mock.patch` or `pytest-mock`
- Do not mock internal service logic

## Guardrail Tests

For every prohibited pattern in `hooks/pre_response_guardrail.py`, there must be:
1. A test with input that contains the prohibited phrase → assert the phrase is blocked/replaced
2. A test with a compliant alternative → assert it passes through unchanged

When adding a new guardrail rule, add the test before or alongside the rule, not after.

## Coverage Expectation

- New code: aim for full coverage of business logic branches
- Hooks: 100% — every rule must have a test
- Existing baseline is the test suite in `tests/` as of the last merged PR
