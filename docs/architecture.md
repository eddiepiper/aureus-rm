# Aureus RM Copilot — Architecture (V5.1)

---

## 1. System Overview

Aureus RM Copilot is a Python Telegram bot backed by the Anthropic API (Claude) and Google Sheets. It gives relationship managers structured, compliance-aware AI assistance for daily RM workflows: client intelligence, equity research, portfolio fit checks, relationship memory, and next best action recommendations.

Aureus is not a trading system, a regulated investment advisor, or a general-purpose chatbot. All outputs are internal RM decision-support tools requiring human review before client use.

---

## 2. High-Level Architecture

```
Telegram User
      │
      ▼
┌─────────────────────────────────┐
│         ChatRouter              │  ← NL resolution + session continuity
│  (RelationshipMemoryService)    │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│        CommandRouter            │  ← 3-tier command dispatch
│  V2 · V3 · V5.1 commands        │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│               AureusOrchestrator                    │
│                                                     │
│   ┌──────────────────────────┐                      │
│   │ Portfolio Counsellor     │  portfolio review    │
│   │ Agent                    │  fit checks          │
│   │                          │  scenario analysis   │
│   └──────────────────────────┘                      │
│   ┌──────────────────────────┐                      │
│   │ Equity Analyst Agent     │  equity deep dives   │
│   │                          │  catalyst analysis   │
│   │                          │  thesis checks       │
│   └──────────────────────────┘                      │
│   ┌──────────────────────────┐                      │
│   │ NBA Agent                │  hybrid scoring      │
│   │                          │  narrative gen       │
│   └──────────────────────────┘                      │
└───────────────────┬─────────────────────────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
┌──────────────────┐  ┌────────────────────┐
│ Relationship     │  │ WritebackService   │
│ MemoryService    │  │ (async, dedup)     │
└──────────────────┘  └────────┬───────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │ Google Sheets  │
                      │ (system of     │
                      │  record)       │
                      └────────────────┘
```

---

## 3. Service Layer

### ChatRouter (`services/chat_router.py`)

Entry point for all Telegram messages. Handles:
- Natural language intent resolution — maps free-text messages to structured commands
- Session continuity — enriches requests with per-client memory context via `RelationshipMemoryService`
- Fallback to direct command dispatch when intent is unambiguous

### CommandRouter (`services/command_router.py`)

3-tier command dispatch:
1. **V2 — Client Intelligence:** `/client_review`, `/portfolio_fit`, `/meeting_pack`, `/next_best_action`
2. **V3 — Equity Research + Wealth Management:** `/earnings_deep_dive`, `/stock_catalyst`, `/thesis_check`, `/idea_generation`, `/morning_note`, `/portfolio_scenario`
3. **V5.1 — Relationship Memory + NBA:** `/relationship_status`, `/overdue_followups`, `/attention_list`, `/morning_rm_brief`, `/log_response`

Falls back to template-based responses if Claude API is unavailable.

### AureusOrchestrator (`services/aureus_orchestrator.py`)

Routes commands to the appropriate specialist agent and synthesises responses. Aureus is the only agent visible to the RM — internal agents are not exposed directly.

When Claude API is unavailable, `CommandRouter` falls back to template-based responses without invoking the orchestrator.

### Specialist Agents

See [docs/agents.md](agents.md) for full descriptions.

| Agent | File | Scope |
|-------|------|-------|
| Portfolio Counsellor | `portfolio_counsellor_agent.py` | Portfolio review, fit checks, scenario analysis |
| Equity Analyst | `equity_analyst_agent.py` | Equity deep dives, catalyst identification, thesis checks |
| NBA Agent | `nba_agent.py` | Next best action scoring + Claude narrative generation |

### RelationshipMemoryService (`services/relationship_memory_service.py`)

Maintains per-client session context across commands within a conversation. Reads relationship state from Google Sheets (`Customers` tab V5.1 columns). Used by both `ChatRouter` (for NL enrichment) and `NBAAgent` (for scoring context).

### WritebackService (`services/writeback_service.py`)

Non-blocking async write-back to Google Sheets. Includes:
- Deduplication guard — prevents double-logging of the same interaction
- Fire-and-forget pattern — Sheets writes do not block bot response delivery

---

## 4. Data Flow — Command Execution

```
1. RM sends Telegram message
       ↓
2. ChatRouter: resolve intent → extract command + args + client context
       ↓
3. CommandRouter: look up handler for the resolved command
       ↓
4. Handler: fetch client data from ClientService / SheetsService
       ↓
5. AureusOrchestrator: route to specialist agent(s) based on command type
       ↓
6. Agent: call ClaudeService with enriched prompt + data context
       ↓
7. (V5.1 commands) NBAAgent: score + generate narrative
       ↓
8. WritebackService: async write interaction log to Sheets (non-blocking)
       ↓
9. Formatted response returned to Telegram
```

---

## 5. Google Sheets Schema

| Tab | Purpose | V5.1 Additions |
|-----|---------|----------------|
| `Customers` | Client profiles, risk profiles, segments | `last_contact_date`, `relationship_status`, `attention_flag`, `attention_reason` |
| `Holdings` | Portfolio holdings, weights, CASA | — |
| `Interactions` | Interaction history, follow-up flags | — |
| `Watchlist` | Client stock watchlist | — |
| `Tasks_NBA` | NBA action items, urgency, due dates | `nba_score` |

Run `python scripts/bootstrap_v51_schema.py` to migrate a live sheet from V4/V5 to V5.1.

---

## 6. Hook Layer

Python hooks enforce compliance on every interaction:

| Hook | When | What |
|------|------|------|
| `pre_response_guardrail.py` | Before response delivery | Blocks prohibited language: buy/sell directives, guaranteed returns, risk-free claims |
| `source_validation.py` | After data retrieval | Validates all cited data was fetched in the current session |
| `crm_logger.py` | After response delivery | Logs completed interactions to the CRM notes system |

---

## 7. Startup Sequence (`app.py`)

1. Load and validate config from environment
2. Connect to Google Sheets — fall back to mock mode if unavailable
3. Initialise Claude API service — fall back to templates if unavailable
4. Initialise V5.1 shared services: `RelationshipMemoryService`, `WritebackService`
5. Initialise specialist agents: `PortfolioCounsellorAgent`, `EquityAnalystAgent`, `NBAAgent`
6. Wire `AureusOrchestrator` and `CommandRouter`
7. Initialise `ChatRouter`
8. Start Telegram bot polling

---

## 8. Technology Stack

| Component | Technology |
|-----------|-----------|
| Bot interface | Telegram (python-telegram-bot) |
| AI generation | Anthropic API — claude-sonnet-4-6 |
| Storage backend | Google Sheets (gspread) |
| Language | Python 3.11+ |
| Containerisation | Docker / docker-compose |
| Test framework | pytest (108 tests) |
| Claude Code integration | `.claude/` (commands, skills, rules, hooks) |
