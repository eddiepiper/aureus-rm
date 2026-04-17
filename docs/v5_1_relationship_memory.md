# V5.1 — Relationship Memory + Next Best Action

**Released:** 2026-04-15

---

## Overview

V5.1 adds a relationship memory layer and next best action system to Aureus. The goal is to shift from reactive, command-by-command assistance to a more continuous RM workflow: the bot maintains context about each client relationship across interactions, scores the book for prioritisation, and surfaces actionable recommendations without the RM needing to manually track follow-up state.

---

## New Services

### RelationshipMemoryService

**File:** `services/relationship_memory_service.py`

Reads and writes per-client relationship state from Google Sheets. Surfaces context in two places:

1. **ChatRouter** — enriches NL message resolution with the current client context so the bot understands mid-session references like "what about the NVDA idea for him?" without re-specifying the client
2. **NBAAgent** — provides the relationship signals used in NBA scoring (last contact date, open follow-ups, attention flags)

Key fields maintained (V5.1 Sheets columns on `Customers` tab):
- `last_contact_date` — date of most recent interaction
- `relationship_status` — current relationship health label
- `attention_flag` — boolean flag for clients requiring urgent attention
- `attention_reason` — free-text reason for the attention flag

### WritebackService

**File:** `services/writeback_service.py`

Async, non-blocking write-back to Google Sheets. Two capabilities:
- **Interaction logging** — appends interaction records to the `Interactions` tab after `/log_response`
- **Task write-back** — appends or updates NBA action items in the `Tasks_NBA` tab

**Deduplication:** A guard prevents double-logging the same interaction. Writes are fire-and-forget — they do not block response delivery to the RM.

### NBAAgent

**File:** `services/nba_agent.py`

Hybrid scoring engine. Architecture:
1. **Rule-based scoring** — deterministic signals computed without Claude: interaction recency, open follow-up count, watchlist activity, overdue tasks, portfolio event triggers
2. **Claude narrative** — Claude is invoked to generate a prioritised, human-readable action narrative based on the scored signals

This design keeps ranking consistent and hallucination-free while still producing natural-language output the RM can act on immediately.

---

## New Commands

### `/relationship_status [client name]`

Full relationship snapshot for a single client: memory context, open follow-ups, recent interactions, NBA recommendations.

Example: `/relationship_status John Tan`

### `/overdue_followups [client name]`

Lists all overdue follow-up actions for a client, ranked by urgency. Pulls from `Tasks_NBA` and `Interactions` tabs.

Example: `/overdue_followups John Tan`

### `/attention_list`

Book-wide view. Ranks all clients by NBA score and surfaces the top-priority attention items. Useful for the RM's morning review.

Example: `/attention_list`

### `/morning_rm_brief`

Daily morning briefing across the full RM book. Combines NBA scoring, upcoming events, and recent interaction gaps into a single prioritised briefing. No arguments required.

Example: `/morning_rm_brief`

### `/log_response [client name] [interested|neutral|declined] [optional ticker]`

Logs a client's response to a recent conversation and updates relationship memory. Creates an interaction record in Sheets and optionally updates watchlist state.

Examples:
```
/log_response John Tan interested NVDA
/log_response Sarah Lim declined
/log_response James Wong neutral
```

---

## ChatRouter: Session Continuity

**File:** `services/chat_router.py`

V5.1 adds a `ChatRouter` layer above `CommandRouter`. It handles:
- **NL intent resolution** — maps free-text messages to structured command + args
- **Session continuity** — if the RM is mid-conversation about a client, subsequent messages are enriched with that client's relationship context automatically
- **Disambiguation** — surfaces options when intent is ambiguous, rather than failing silently

---

## Google Sheets Migration

V5.1 adds columns to existing tabs. Run the migration script before using relationship memory features on a live sheet:

```bash
venv/bin/python scripts/bootstrap_v51_schema.py
```

New columns added:
- `Customers`: `last_contact_date`, `relationship_status`, `attention_flag`, `attention_reason`
- `Tasks_NBA`: `nba_score`

The script is non-destructive — existing data is preserved. Idempotent: safe to run multiple times.

---

## Tests

108 unit tests cover:
- `NBAAgent` scoring logic — rule weights, edge cases, score normalisation
- `WritebackService` — deduplication guard, async behaviour
- `ChatRouter` — NL resolution, session context enrichment

```bash
venv/bin/python -m pytest tests/ -q
```
