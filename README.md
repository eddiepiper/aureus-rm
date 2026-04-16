# Aureus RM Copilot

## Security & Setup

**Never commit secrets.** This repo is designed to be public-safe out of the box.

| File | Status | Notes |
|------|--------|-------|
| `.env` | Excluded by `.gitignore` | Contains all secrets |
| `credentials/*.json` | Excluded by `.gitignore` | Google service account key |
| `.env.example` | Safe to commit | Placeholders only, no values |

### First-time setup

```bash
# 1. Copy the example env file and fill in your values
cp .env.example .env

# 2. Place your Google service account key
# (see credentials/README.md for how to obtain it)
cp ~/Downloads/your-service-account.json credentials/service-account.json
```

Your `.env` should contain:

```
TELEGRAM_BOT_TOKEN=        # from @BotFather
GOOGLE_SHEETS_SPREADSHEET_ID=  # from the sheet URL
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
ANTHROPIC_API_KEY=         # from console.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_MAX_TOKENS=1024
```

If `GOOGLE_SHEETS_SPREADSHEET_ID` is left blank, the bot runs in **mock mode** using sample data.

---

## Quick Start (Docker)

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# edit .env: add TELEGRAM_BOT_TOKEN and GOOGLE_SHEETS_SPREADSHEET_ID

# 2. Place Google service account credentials
cp your-service-account.json credentials/service-account.json

# 3. Build and run
docker compose up --build
```

The bot starts polling. Open Telegram, find your bot, and type `/start`.

If Google Sheets credentials are unavailable, the bot runs in **mock mode** using sample data for John Tan (CUST001).

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From @BotFather on Telegram |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Yes | ID from the spreadsheet URL |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Default: `/app/credentials/service-account.json` |
| `APP_ENV` | No | `dev` or `prod` (default: `dev`) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING` (default: `INFO`) |

---

## Credentials Setup

1. Create a Google Cloud service account and download the JSON key
2. Place it at `credentials/service-account.json`
3. Share your Google Spreadsheet with the service account `client_email`
4. See `credentials/README.md` for full instructions

---

## Telegram Commands (MVP)

| Command | Usage | Purpose |
|---------|-------|---------|
| `/start` | `/start` | Welcome message |
| `/help` | `/help` | Show available commands |
| `/client_review` | `/client_review John Tan` | Full client review |
| `/portfolio_fit` | `/portfolio_fit John Tan D05.SI` | Portfolio fit check |
| `/meeting_pack` | `/meeting_pack John Tan` | Meeting prep pack |
| `/next_best_action` | `/next_best_action John Tan` | Next best actions |

---

## Google Sheets Structure

The bot reads from a Google Spreadsheet with these 5 tabs:

| Tab | Key Columns |
|-----|-------------|
| `Customers` | `customer_id`, `full_name`, `telegram_chat_id`, `risk_profile`, `segment`, … |
| `Holdings` | `customer_id`, `ticker`, `security_name`, `portfolio_weight_pct`, … |
| `Interactions` | `customer_id`, `interaction_date`, `channel`, `summary`, `follow_up_required`, … |
| `Watchlist` | `customer_id`, `ticker`, `security_name`, `reason_for_interest`, … |
| `Tasks_NBA` | `customer_id`, `action_title`, `urgency`, `status`, `due_date`, … |

`customer_id` is the join key across all tabs. The first row of each tab must be a header row matching the column names above.

---

## How to Test

**With mock data (no credentials needed):**
- Leave `GOOGLE_SHEETS_SPREADSHEET_ID` empty or omit `service-account.json`
- The bot will start in mock mode with sample client John Tan (CUST001)
- Try: `/client_review John Tan`

**With real data:**
- Populate your Google Sheet with the tab structure above
- Set credentials and spreadsheet ID in `.env`
- Run `docker compose up --build`

---

## MVP Limitations

- Stock data (prices, fundamentals) is not live — `/portfolio_fit` shows portfolio context only
- No Claude API integration yet — commands use structured Sheets data, not LLM reasoning
- Single-user only — no RM identity or access control
- No write-back to CRM (logging to console only in MVP)
- Telegram only — no web UI

---

## What This Is

Aureus RM Copilot is a Claude Code–integrated assistant for relationship managers and wealth advisors. It provides structured, compliance-aware AI assistance for daily RM workflows: client meeting preparation, stock analysis, portfolio suitability checks, earnings summaries, and next-best-action planning.

All outputs are grounded in live data pulled from internal connectors (CRM, portfolio, suitability, house view, compliance) and external market data sources. Every response carries required disclosures and is validated against internal compliance framing rules before delivery.

---

## What This Is Not

- **Not a trading system.** No orders are placed or routed.
- **Not a regulated investment advisor.** Outputs are decision-support tools for qualified RMs, not client-facing advice.
- **Not a replacement for RM judgment.** All outputs require human review before use with clients.
- **Not a general-purpose chatbot.** Commands and skills are scoped strictly to RM workflows. Out-of-scope queries are rejected.
- **Not production-ready without connector implementation.** All MCP server entries in `.mcp.json` are currently placeholders. See [Connectors and Extension Points](#connectors-and-extension-points).

---

## Who It Is For

- **Relationship managers** preparing for client meetings or responding to inbound client inquiries
- **Wealth advisors** evaluating stock ideas against client mandates
- **RM team leads** monitoring action item pipelines and coverage quality
- **Internal build teams** extending the system with new connectors or commands

---

## Available Commands

| Command | Syntax | Purpose |
|---|---|---|
| `client-review` | `/client-review [client_id or name]` | Full RM review summary: holdings snapshot, recent interactions, open follow-ups, relationship health |
| `stock-brief` | `/stock-brief [TICKER]` | Concise stock brief: snapshot, key metrics, house view, recent news, risks |
| `portfolio-fit` | `/portfolio-fit [TICKER] [client_id]` | Evaluate whether a stock fits a specific client's mandate, concentration limits, and sector constraints |
| `compare-stocks` | `/compare-stocks [TICKER_A] [TICKER_B]` | Side-by-side fundamental and qualitative comparison of two stocks |
| `meeting-pack` | `/meeting-pack [client_id] [meeting_date]` | Full meeting pack: client brief, portfolio summary, talking points, agenda, suggested actions |
| `next-best-action` | `/next-best-action [client_id]` | Prioritised next-best-action recommendations based on portfolio state, interactions, and market events |
| `risk-check` | `/risk-check [TICKER] [client_id]` | Identify suitability, concentration, disclosure, and house view risks before discussing a stock with a client |
| `earnings-update` | `/earnings-update [TICKER] [quarter]` | Structured earnings summary formatted for RM internal use: beat/miss, guidance, key themes, talking points |

---

## Architecture Overview

Aureus is structured around three Claude Code integration layers, all defined under `.claude/`:

1. **Commands** — user-invoked workflows defined as prompt templates in `.claude/commands/`. Each command specifies the tools it calls, the output schema it targets, and the compliance framing it applies.
2. **Skills** — reusable reasoning modules in `.claude/skills/` that commands invoke for shared logic (e.g. suitability assessment, output formatting, house view integration).
3. **Hooks** — lifecycle interceptors in `hooks/` that enforce guardrails, validate sources, and log activity to CRM on every response cycle.

MCP servers defined in `.mcp.json` provide the data layer. Aureus does not embed data — all client, portfolio, market, and compliance data is fetched at runtime via MCP tool calls.

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram, data flow, and component dependency map.

---

## Guardrails and Compliance

Three hook layers enforce compliance on every interaction:

- **`pre_response_guardrail.py`** — blocks responses that use prohibited language (buy/sell directives, performance guarantees, speculative price targets) or that address out-of-scope topics.
- **`source_validation.py`** — validates that all data cited in a response was fetched from an authorised MCP tool call in the current session. Rejects responses that cite stale or unattributed data.
- **`crm_logger.py`** — logs every completed response to the internal notes system via `notes.save_meeting_prep` or `notes.save_action_item`, depending on command type.

All three guardrail behaviors — disclaimer enforcement, prohibited language checking, and source attribution — are active by default. Compliance rules are defined in `.claude/rules/compliance.md`.

See [docs/guardrails.md](docs/guardrails.md) for the full prohibited language list, disclaimer templates, and escalation paths.

---

## Connectors and Extension Points

Nine MCP servers are declared in `.mcp.json`. All are currently marked `"placeholder": true` and require real transport and authentication configuration before use:

| Server | Purpose |
|---|---|
| `crm` | Client profiles and interaction history |
| `portfolio` | Holdings, weights, unrealised P&L, exposure breakdown |
| `suitability` | Risk profiles, mandates, sector exclusions |
| `market` | Company snapshots, price history |
| `fundamentals` | Financials, estimates, consensus data |
| `research` | Earnings summaries, news search |
| `house_view` | Internal house view ratings and commentary |
| `compliance` | Disclosure checks, approved product lists |
| `notes` | Meeting prep save, action item logging |

To wire a connector: replace `"command": "placeholder"` with the actual binary or script path, populate `"args"` with auth and endpoint configuration, and remove `"placeholder": true`.

See [docs/connector-requirements.md](docs/connector-requirements.md) for per-connector interface contracts, expected response shapes, and authentication patterns.

---

## How to Test

**Prerequisites:** Claude Code CLI installed and authenticated. Open the repo in Claude Code — `.claude/` is loaded automatically.

**1. Smoke test a command (no live connectors required)**

With placeholder connectors active, commands will return structured prompts with empty data slots. This validates command routing, skill loading, and hook execution:
```
/stock-brief AAPL
/client-review test-client-001
```

**3. Test with stub connectors**

Point each MCP server at a local stub that returns fixture JSON matching the output schemas in `schemas/`. Fixture data for each schema is available in `examples/sample-outputs.md`.

**4. Validate hooks**

- Attempt a response containing a prohibited phrase (e.g. "you should buy") — `pre_response_guardrail` should block it.
- Attempt a response citing data not fetched in-session — `source_validation` should reject it.
- Confirm a successful response logs to `notes` — check `crm_logger` stdout or stub CRM log.

**5. End-to-end**

Wire at least `crm`, `portfolio`, and `suitability` to real or staging endpoints and run `/meeting-pack [client_id] [date]`. Validate the output matches the `meeting_pack` schema in `schemas/meeting_pack.json`.

---

## Project Structure

```
aureus-rm/
├── .claude/                     # Claude Code integration (commands, skills, agents, rules, hooks)
├── .mcp.json                    # MCP server declarations (9 connectors, all placeholder)
├── README.md
│
├── commands/                    # One file per slash command — prompt template + tool call spec
│   ├── client-review.md
│   ├── compare-stocks.md
│   ├── earnings-update.md
│   ├── meeting-pack.md
│   ├── next-best-action.md
│   ├── portfolio-fit.md
│   ├── risk-check.md
│   └── stock-brief.md
│
├── skills/                      # Reusable reasoning modules loaded by commands
│   ├── house-view-integration.md
│   ├── next-best-action-framework.md
│   ├── output-formatting-rules.md
│   ├── portfolio-concentration-check.md
│   ├── rm-client-meeting-prep.md
│   ├── stock-analysis-framework.md
│   └── suitability-response-style.md
│
├── hooks/                       # Lifecycle interceptors (pre_response, post_tool_call, post_response)
│   ├── crm_logger.py
│   ├── pre_response_guardrail.py
│   └── source_validation.py
│
├── schemas/                     # JSON Schemas for structured command outputs
│   ├── client_context.json
│   ├── meeting_pack.json
│   ├── next_best_action.json
│   ├── portfolio_fit.json
│   └── stock_brief.json
│
├── docs/
│   ├── architecture.md          # System architecture, data flow, component map
│   ├── connector-requirements.md # Per-connector interface contracts and auth patterns
│   ├── guardrails.md            # Prohibited language list, disclaimer templates, escalation
│   └── implementation-plan.md   # Phased build-out plan
│
└── examples/
    ├── example-prompts.md       # Sample RM prompts for each command
    └── sample-outputs.md        # Fixture outputs for testing and schema validation
```

---

## Assumptions and Limitations

- **Connector data quality is the ceiling.** Output quality is bounded by the completeness and freshness of data returned by MCP connectors. Stale CRM data or missing suitability profiles will degrade outputs.
- **Single-client context per session.** Commands are designed around one client per invocation. Multi-client batch workflows are not supported in v0.1.
- **No persistent memory across sessions.** Aureus does not maintain conversation state between sessions. Each command invocation is stateless; prior context must be re-supplied or fetched via CRM tools.
- **House view dependency.** `portfolio-fit`, `risk-check`, and `stock-brief` assume a `house_view` connector is available. Without it, these commands will omit internal view data and flag the gap in output.
- **Compliance hook scope.** The guardrail hook intercepts Claude-generated text only. It does not validate raw data returned by MCP tools. Data quality and PII handling in connectors are the responsibility of the connector implementation layer.
- **Schema version pinning.** All schemas are at v0.1. Breaking changes to connector output shapes will require coordinated schema and command updates.
- **No multi-currency normalisation.** Portfolio values are returned in the currency reported by the `portfolio` connector. Cross-currency aggregation is not performed.
