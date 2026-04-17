# Aureus RM Copilot — Version History

---

## V5.1 — Relationship Memory Layer + Next Best Action
**Released:** 2026-04-15 | **Branch:** main (merged via PR #4)

### What shipped
- **RelationshipMemoryService** — per-client session context maintained across commands; reads from and writes to Google Sheets V5.1 columns
- **NBAAgent** — hybrid scoring engine: deterministic rule-based scoring + Claude narrative generation for next best action recommendations
- **WritebackService** — async, non-blocking write-back to Google Sheets with deduplication guard
- **ChatRouter** — natural language intent resolution + session continuity enrichment via relationship memory
- **5 new RM workflows:**
  - `/relationship_status` — full relationship snapshot: memory context, open follow-ups, NBA
  - `/overdue_followups` — flags overdue follow-up actions for a client
  - `/attention_list` — book-wide prioritised client list ranked by NBA scoring
  - `/morning_rm_brief` — daily morning briefing across the full RM book
  - `/log_response` — log client response (interested / neutral / declined) and update relationship memory
- **V5.1 schema migration** — non-disruptive column additions to live Sheets (`bootstrap_v51_schema.py`)
- **108 unit tests** covering NBAAgent scoring, WritebackService deduplication, ChatRouter NL resolution

### Architecture change
3-tier command dispatch added to `CommandRouter`; `ChatRouter` layer added above command routing for NL resolution and session continuity.

---

## V5 — Aureus Orchestrator + Two-Agent Architecture
**Released:** 2026-04-14

### What shipped
- **AureusOrchestrator** — central routing layer; dispatches commands to specialist agents and synthesises responses; sole user-facing assistant
- **PortfolioCounsellorAgent** — handles portfolio review, scenario analysis, and stock fit checks
- **EquityAnalystAgent** — handles equity deep dives, catalyst identification, and thesis validation
- **ClaudeService extended** — multi-agent support; shared Claude API access across agents
- Bug fix: customer name parsing failure when multiple commands submitted together

### Architecture change
Replaced direct-to-Claude command execution with an orchestrator + specialist agent model.

---

## V4 — CASA Liquidity + Signature Output Style
**Released:** 2026-04-01

### What shipped
- **CASA liquidity tracking** — current account / savings account deployable cash tracked per client
- **Liquidity-aware reasoning** — CASA buffer injected into portfolio scenario prompts and idea generation
- **Mock data updated** — all sample clients include deployable cash holdings
- **Google Sheets bootstrapped** — live sheet schema updated with CASA-enabled columns
- **Aureus Signature Output Style** — institutional-quality system prompt for all command outputs
- **Command prompts rewritten** — all commands enforce Signature Output Style
- **Max tokens increased** — supports longer, richer responses

---

## Recommended Next Phase: V6 Workflow Agent

V6 is not yet built. Recommended scope:

- **Scheduled morning brief** — pushed to RM at a set time without requiring a command
- **Proactive alerts** — price moves, earnings calendar, client anniversary / review triggers
- **Multi-client batch processing** — nightly full-book scan
- **Persistent workflow state** — open action items tracked across sessions, not just in-memory
- **Calendar and CRM integration** — Google Calendar, HubSpot, or equivalent
- **Escalation routing** — high-priority NBA items flagged to RM manager
