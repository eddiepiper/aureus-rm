# Aureus RM Copilot

Compliance-aware AI copilot for relationship managers and wealth advisors. Decision-support tooling — not a trading system, investment advisor, or general chatbot. All outputs require RM review before client use.

---

## Project Layout

| Path | Purpose |
|------|---------|
| `app.py` | Entry point — boots services and starts the Telegram bot |
| `.claude/commands/` | Slash command prompt templates (9 commands) |
| `.claude/skills/` | Reusable reasoning modules loaded per command |
| `hooks/` | Python lifecycle hooks (guardrail, source validation, CRM logger) |
| `services/` | Service layer — orchestration, agents, financial analysis, CRM |
| `schemas/` | JSON Schema definitions for output validation |
| `docs/` | Architecture, guardrails, connector requirements |
| `.mcp.json` | MCP server declarations (9 connectors — all placeholder in dev) |
| `.claude/rules/` | Active rules Claude must follow when working in this repo |
| `.claude/agents/` | Agent role definitions for structured review and analysis tasks |

---

## Commands

| Command | File | Purpose |
|---------|------|---------|
| `/client-review` | `.claude/commands/client-review.md` | RM review summary for a client |
| `/stock-brief` | `.claude/commands/stock-brief.md` | Concise stock brief for a ticker |
| `/portfolio-fit` | `.claude/commands/portfolio-fit.md` | Stock fit evaluation for a client portfolio |
| `/compare-stocks` | `.claude/commands/compare-stocks.md` | Side-by-side stock comparison |
| `/meeting-pack` | `.claude/commands/meeting-pack.md` | Full meeting pack for client |
| `/next-best-action` | `.claude/commands/next-best-action.md` | Next-best-action suggestions for RM |
| `/risk-check` | `.claude/commands/risk-check.md` | Risk considerations before discussing a stock |
| `/earnings-update` | `.claude/commands/earnings-update.md` | Earnings summary for banker use |
| `/ai_assessment` | `.claude/commands/ai-assessment.md` | Accredited Investor eligibility assessment |

**AI Assessment rules:** Read `.claude/rules/compliance.md` and `.claude/commands/ai-assessment.md` before generating any AI assessment output. The assessment is criterion-specific; never auto-switch to another criterion.

---

## Critical Rules

- **Compliance:** Read `.claude/rules/compliance.md` before generating any output that discusses securities, suitability, or forward-looking statements
- **Data sourcing:** Every data claim must trace to an MCP tool call made in the current session — never infer or carry over from prior context
- **Output framing:** All outputs are for RM internal use only — never frame as direct client advice, buy/sell recommendations, or guaranteed outcomes
- **Missing data:** State gaps explicitly (`"Data not available from [source]"`) — do not substitute or fabricate
- **Formatting:** Follow `.claude/skills/output-formatting-rules.md` for all command outputs

## Do Not

- Generate guaranteed return language, risk-free claims, or explicit buy/sell directives
- Modify `hooks/pre_response_guardrail.py` prohibited patterns without adding a test in `tests/`
- Touch `.claude/settings.local.json` — it contains hand-crafted permissions and MCP config
- Touch `.env` or `credentials/` — secrets, gitignored

---

## Development

```bash
# Install dependencies
python3 -m venv venv && venv/bin/pip install -r requirements.txt

# Run with mock MCP server
venv/bin/python app.py

# Run full test suite
python -m pytest tests/ -q

# Run specific test suite
python -m pytest tests/test_financial_analysis_service.py -v
```

## Python Hooks (Runtime)

These execute as part of the plugin lifecycle — they are Python modules, not bash hooks:

- `hooks/pre_response_guardrail.py` — blocks prohibited language patterns before response delivery
- `hooks/source_validation.py` — validates all cited data was fetched from MCP tools this session
- `hooks/crm_logger.py` — logs completed interactions to the CRM notes system

To add a guardrail rule: update `hooks/pre_response_guardrail.py` → add entry to `docs/guardrails.md` → write test in `tests/test_guardrail.py`.
