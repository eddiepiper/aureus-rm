# Aureus RM Copilot — Architecture

---

## 1. System Overview

Aureus RM Copilot is a Claude Code plugin that gives relationship managers structured, compliance-aware AI assistance for their daily workflows: client meeting preparation, stock analysis, portfolio suitability checks, earnings summaries, and next-best-action planning. It solves the RM productivity problem — the time and cognitive load required to pull together client context, market data, and portfolio observations before a meeting or client call — by automating data retrieval and output structuring against a consistent, compliance-enforced template. Aureus is not a trading system, a regulated investment advisor, or a general-purpose chatbot. It is a decision-support layer for qualified RMs. All outputs require human review before use with clients. The plugin does not place orders, generate regulated advice, or operate without a human in the loop.

---

## 2. Agent Architecture

Aureus uses five internal agent roles. These are not separate processes — they are logical roles that Claude Code fulfils in sequence during a single command execution, governed by the command file, loaded skills, and active hooks.

---

### Client Context Agent

**Responsibilities:**
- Fetch and normalise client profile data from CRM
- Retrieve recent interaction history and open follow-up items
- Identify suitability constraints, mandate rules, and active exclusions
- Surface relationship flags (overdue follow-ups, upcoming reviews, stated preferences)

**Inputs:** `client_name` or `client_id` from the command invocation

**Outputs:** Structured client context block used by downstream agents — segment, AUM band, risk rating, mandate constraints, interaction history, open follow-ups

**Primary MCP tools:**
- `crm.get_client_profile(client_name)`
- `crm.get_recent_interactions(client_name, limit=5)`
- `suitability.get_risk_profile(client_name)`

---

### Market Research Agent

**Responsibilities:**
- Fetch company snapshots, price history, and sector data for named tickers
- Retrieve recent news and research events (last 30 days by default)
- Pull consensus analyst estimates and earnings data
- Surface macro or sector themes relevant to the client's portfolio

**Inputs:** Ticker symbol(s) from command arguments or derived from portfolio holdings

**Outputs:** Stock-level data blocks — business overview, performance data, financials, estimates, recent news — used by stock-facing commands and meeting pack generation

**Primary MCP tools:**
- `market.get_company_snapshot(ticker)`
- `market.get_price_history(ticker, period)`
- `research.search_news(ticker, days=30)`
- `research.get_earnings_summary(ticker, quarter)`

---

### Portfolio Analysis Agent

**Responsibilities:**
- Retrieve current holdings and compute sector/geographic exposure breakdowns
- Identify concentration risks: single-name, sector, geographic
- Assess the impact of adding a new position on portfolio diversification
- Flag threshold breaches against mandate-defined concentration limits

**Inputs:** Client identifier; optionally, a ticker for fit analysis

**Outputs:** Holdings table, exposure breakdown, concentration flags, diversification assessment

**Primary MCP tools:**
- `portfolio.get_holdings(client_name)`
- `portfolio.get_exposure_breakdown(client_name)`

**Skills invoked:** `portfolio-concentration-check.md`

---

### Suitability and Guardrails Agent

**Responsibilities:**
- Validate that proposed discussion topics are consistent with the client's risk profile and mandate
- Check stocks against active exclusion criteria (sector, ESG, geographic, product type)
- Run compliance disclosure checks before output is generated
- Apply the `pre_response_guardrail` hook to block or flag non-compliant language in the draft response
- Enforce missing data behaviour (note gaps; do not infer or fabricate)

**Inputs:** Client suitability profile, ticker compliance data, draft response text

**Outputs:** Fit assessment (Fits / Partially Fits / Does Not Fit), compliance notes, guardrail pass/fail signal, required disclaimer flags

**Primary MCP tools:**
- `suitability.get_risk_profile(client_name)`
- `suitability.validate_recommendation_framing(text)`
- `compliance.check_disclosures(client_name, ticker)`

**Skills invoked:** `suitability-response-style.md`

**Hook:** `pre_response_guardrail.py` (pre-response)

---

### Output and Reporting Agent

**Responsibilities:**
- Assemble all upstream data blocks into the command's specified output format
- Apply house view data to relevant sections
- Append required disclaimers
- Log completed output to the CRM notes system
- Ensure output adheres to formatting rules (markdown structure, section headers, table format)

**Inputs:** All upstream agent outputs, house view data, command output template

**Outputs:** Final structured markdown response delivered to the RM; CRM log entry written via `notes` connector

**Primary MCP tools:**
- `house_view.get_internal_view(ticker)`
- `notes.save_meeting_prep(client_name, output)`

**Skills invoked:** `output-formatting-rules.md`, `house-view-integration.md`

**Hook:** `crm_logger.py` (post-response)

---

## 3. Data Flow

```
User invokes command (e.g. /portfolio-fit "James Tan" D05.SI)
        |
        v
Plugin manifest (plugin.json) routes to commands/portfolio-fit.md
        |
        v
Skills loaded: portfolio-concentration-check.md, suitability-response-style.md,
               output-formatting-rules.md
        |
        v
┌─────────────────────────────────────────────────────────────┐
│  DATA RETRIEVAL (parallel where possible)                   │
│                                                             │
│  crm.get_client_profile()        → client profile block     │
│  suitability.get_risk_profile()  → mandate + constraints    │
│  portfolio.get_holdings()        → current holdings         │
│  portfolio.get_exposure_breakdown() → sector/geo weights    │
│  market.get_company_snapshot()   → stock profile            │
│  fundamentals.get_financials()   → financial data           │
│  compliance.check_disclosures()  → disclosure flags         │
│  house_view.get_internal_view()  → internal view            │
└─────────────────────────────────────────────────────────────┘
        |
        v
source_validation.py hook — validates all cited data was fetched
this session from authorised MCP tools
        |
        v
Draft response assembled per command output template
        |
        v
pre_response_guardrail.py hook — scans draft for prohibited
language, missing disclaimers, suitability violations
        |
    ┌───┴───┐
  BLOCK   PASS
    |       |
    v       v
Error    Final response delivered to RM
         + disclaimer block appended
              |
              v
         crm_logger.py hook — logs output to
         notes.save_meeting_prep() or notes.save_action_item()
```

---

## 4. Command Execution Flow

1. **User invokes command** — types `/portfolio-fit "James Tan" D05.SI` in Claude Code
2. **Plugin manifest loads** — `plugin.json` maps the command name to `commands/portfolio-fit.md` and loads the declared skills
3. **Argument parsing** — command template extracts `client_name = "James Tan"` and `ticker = "D05.SI"`
4. **Skills applied** — `portfolio-concentration-check.md`, `suitability-response-style.md`, and `output-formatting-rules.md` are injected into the model context as reasoning guides
5. **MCP tool calls execute** — the model calls each tool specified in the command's Data Retrieval Steps in order (or in parallel where the command permits); tool responses are collected
6. **`source_validation.py` hook runs** (post-tool-call) — verifies that all data references in the forming response correspond to tool calls made in the current session; rejects unattributed or stale citations
7. **Draft response assembled** — model structures output against the command's Output Format specification, filling sections from tool call results; gaps are noted explicitly
8. **`pre_response_guardrail.py` hook runs** (pre-response) — scans assembled draft for prohibited language patterns, missing disclaimers, and suitability violations; blocks or warns as configured
9. **Output delivered to RM** — passing response rendered in Claude Code with standard disclaimer appended
10. **`crm_logger.py` hook runs** (post-response) — calls `notes.save_meeting_prep()` or `notes.save_action_item()` to log the completed interaction to CRM

---

## 5. Hook Execution Points

### `pre_response_guardrail.py`

**When it runs:** After the model has assembled a draft response, before the response is delivered to the user.

**What it checks:**
- Presence of prohibited language patterns (e.g. "you should buy", "guaranteed return", "will go up", "risk-free", price targets stated as fact)
- Missing required disclaimer block
- Responses that function as direct buy/sell recommendations rather than RM discussion support
- Out-of-scope content (financial advice not tied to an RM workflow, unrelated topics)
- Suitability constraint violations visible in the response text (e.g. recommending a stock that the client's mandate explicitly excludes)

**What it can block:** Any response that matches a prohibited pattern is blocked and replaced with an error message explaining which rule was triggered. The RM is instructed to rephrase or escalate. Responses that trigger a warning (softer violations) are passed through with a prepended flag visible to the RM.

---

### `source_validation.py`

**When it runs:** After MCP tool calls complete, before draft response assembly.

**What it validates:**
- Every data point referenced in the forming response has a corresponding MCP tool call result from the current session
- No data is cited without a traceable source (no hallucinated figures, no data carried over from prior sessions)
- Tool call results are not mixed across different client contexts in multi-step sessions

**What it rejects:** Any response that cites data not fetched in-session, or that cannot be traced to a specific tool call result, is rejected with a source attribution error.

---

### `crm_logger.py`

**When it runs:** After a response has been successfully delivered to the RM.

**What it logs:**
- Command name and arguments
- Timestamp of execution
- Summary of tool calls made and data sources accessed
- The response output (or a truncated version, depending on configuration)
- Any guardrail warnings that were surfaced (even if the response passed)

**Where it writes:** Calls `notes.save_meeting_prep(client_name, output)` for meeting-related commands (`/meeting-pack`, `/client-review`) and `notes.save_action_item(client_name, action_summary)` for action-oriented commands (`/next-best-action`). For commands that are not client-specific (e.g. `/stock-brief`, `/earnings-update`), the logger writes a general activity log entry.

---

## 6. MCP Tool Architecture

### Tool Categories

| Category | Server | Purpose |
|---|---|---|
| CRM | `crm` | Client profiles, interaction history |
| Portfolio | `portfolio` | Holdings, exposure breakdowns |
| Suitability | `suitability` | Risk profiles, mandate validation, recommendation framing checks |
| Market | `market` | Company snapshots, price history |
| Fundamentals | `fundamentals` | Financials, analyst estimates |
| Research | `research` | Earnings summaries, news search |
| HouseView | `house_view` | Internal view ratings and commentary |
| Compliance | `compliance` | Disclosure checks, approved product lists |
| Notes | `notes` | Meeting prep save, action item logging |

### Placeholder vs Live Connector Distinction

All nine MCP servers declared in `.mcp.json` are currently `"placeholder": true`. A placeholder connector:
- Is declared in the manifest and accepted by the plugin
- Will be called by the model at the appropriate step in a command
- Returns an empty or stub response (no actual data)
- Causes the command to note "Data not available from source" in the relevant section
- Does not error or block command execution

A live connector replaces the placeholder transport and authentication configuration with a real implementation that returns data matching the schemas in `schemas/` and the interface contracts in `docs/connector-requirements.md`.

### How to Replace Placeholders with Real Connectors

1. Open `.mcp.json`
2. Locate the server entry (e.g. `"crm"`)
3. Replace `"command": "placeholder"` with the actual binary or script path that starts the MCP server (e.g. `"command": "python"`, `"args": ["connectors/crm_server.py"]`)
4. Populate `"env"` with required authentication environment variables (API keys, endpoint URLs)
5. Remove `"placeholder": true`
6. Verify the connector's output matches the expected response shape documented in `docs/connector-requirements.md`
7. Run a smoke test command with the live connector and validate output against the relevant schema in `schemas/`

---

## 7. Extension Points

### How to Add a New Command

1. Create a new file in `commands/` named `[command-name].md`
2. Define: command purpose, Data Retrieval Steps (list of MCP tool calls with arguments), Output Format (exact section headers and content rules), and Behavioral Rules
3. Register the command in `.claude-plugin/plugin.json` under `"commands"`, mapping the slash command name to the file path and listing which skills to load
4. If the command requires a new output schema, add the schema to `schemas/`
5. Test with placeholder connectors first to validate routing and skill loading

### How to Add a New MCP Connector

1. Implement an MCP server that exposes the required tools (see `docs/connector-requirements.md` for interface contracts)
2. Add the server entry to `.mcp.json` with transport configuration and authentication
3. Add the new tool calls to any commands or skills that should use them
4. Document the connector in `docs/connector-requirements.md`
5. Add schema validation tests for the connector's output shapes

### How to Add a New Guardrail Rule

1. Open `hooks/pre_response_guardrail.py`
2. Add the prohibited pattern to the appropriate rule category (language patterns, scope rules, or suitability rules)
3. Set the action: `"block"` to reject the response entirely, or `"warn"` to pass through with a prepended flag
4. Add the rule to `docs/guardrails.md` with the prohibited example and the compliant alternative
5. Write a unit test in `tests/test_guardrail.py` that confirms the rule triggers correctly on a sample input

### How to Add a New Schema

1. Create a new JSON Schema file in `schemas/` following the existing naming convention (`[command_name].json`)
2. Define all required output fields with types and descriptions
3. Reference the schema in the relevant command file under the Output Format section
4. Register the schema in `plugin.json` under `"schemas"`
5. Add fixture data for the schema to `examples/sample-outputs.md` to support stub connector testing

---

## 8. Technology Stack

| Component | Technology |
|---|---|
| AI runtime | Claude Code (Anthropic) |
| Plugin format | Claude Code plugin manifest (`plugin.json`) |
| Command templates | Markdown prompt files (`commands/*.md`) |
| Reasoning modules (skills) | Markdown instruction files (`skills/*.md`) |
| Lifecycle hooks | Python 3 scripts (`hooks/*.py`) |
| Data connectors | MCP (Model Context Protocol) servers (`mcp.json`) |
| Output schemas | JSON Schema (`schemas/*.json`) |
| Documentation | Markdown (`docs/*.md`) |
| Fixture data | Markdown (`examples/*.md`) |

The plugin has no runtime dependencies beyond Python 3 (for hooks) and a Claude Code installation with MCP support. All data handling is delegated to MCP connector implementations, which may use any language or transport. No database, message queue, or background process is required by the plugin itself.
