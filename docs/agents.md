# Aureus RM Copilot — Agents

Aureus uses a layered agent model. **AureusOrchestrator** is the only agent visible to the RM. Internal specialist agents are not invoked directly — the orchestrator routes to them and synthesises the response.

---

## AureusOrchestrator

**File:** `services/aureus_orchestrator.py`

The central coordination layer. Receives a command and context from `CommandRouter`, determines which specialist agent(s) to invoke, and assembles the final response for delivery to the RM.

**Routing logic:**
- Equity-focused commands → `EquityAnalystAgent`
- Portfolio and client-facing commands → `PortfolioCounsellorAgent`
- NBA and relationship commands → `NBAAgent` (with `RelationshipMemoryService` context)
- Complex commands may invoke multiple agents and synthesise their outputs

**Fallback:** If Claude API is unavailable, `CommandRouter` bypasses the orchestrator and falls back to template-based responses.

---

## Portfolio Counsellor Agent

**File:** `services/portfolio_counsellor_agent.py`

Handles portfolio-oriented reasoning tasks.

**Responsibilities:**
- Full client portfolio review with holdings context
- Stock fit evaluation against client mandate, risk profile, and concentration limits
- Portfolio scenario analysis including CASA liquidity buffer
- Meeting pack generation: briefing, talking points, suggested actions

**Commands primarily routed here:**
- `/client_review`
- `/portfolio_fit`
- `/meeting_pack`
- `/portfolio_scenario`

---

## Equity Analyst Agent

**File:** `services/equity_analyst_agent.py`

Handles equity-specific research and analysis tasks.

**Responsibilities:**
- Earnings deep dives with model implications
- Near-term catalyst identification
- Investment thesis validation
- Stock idea generation based on client mandate and available liquidity
- Morning briefing notes for tickers or sectors

**Commands primarily routed here:**
- `/earnings_deep_dive`
- `/stock_catalyst`
- `/thesis_check`
- `/idea_generation`
- `/morning_note`

---

## NBA Agent

**File:** `services/nba_agent.py`

Hybrid next best action engine combining rule-based scoring with Claude narrative generation.

**Responsibilities:**
- Score each client relationship on a set of deterministic signals (interaction recency, open follow-ups, watchlist activity, portfolio events)
- Generate a prioritised action narrative using Claude
- Power the book-wide attention list and morning brief ranking
- Feed NBA context into `/relationship_status` and `/client_review` outputs

**Commands primarily routed here:**
- `/next_best_action`
- `/attention_list`
- `/morning_rm_brief`
- `/relationship_status`

**Design:** Deterministic scoring ensures consistent ranking without hallucination risk. Claude is invoked only for narrative framing, not for scoring logic.

**Dependencies:** `RelationshipMemoryService` (client context), `ClaudeService` (narrative generation)

---

## Supporting Services

These are not agents but are integral to the V5.1 architecture.

### RelationshipMemoryService

**File:** `services/relationship_memory_service.py`

Maintains per-client relationship context across commands within a session. Reads V5.1 columns from Google Sheets (`last_contact_date`, `relationship_status`, `attention_flag`, `attention_reason`). Used by `ChatRouter` for NL enrichment and by `NBAAgent` for scoring context.

### WritebackService

**File:** `services/writeback_service.py`

Non-blocking async write-back to Google Sheets. Prevents duplicate interaction logs via a deduplication guard. Sheets writes fire-and-forget — they do not block bot response delivery.
