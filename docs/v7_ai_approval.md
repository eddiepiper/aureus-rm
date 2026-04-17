# V7 — AI Approval Agent: Accredited Investor Assessment

**Released:** 2026-04-16 | **Phase:** 1 (structured data) | **Phase 2/3:** document ingestion (future)

---

## Overview

V7 adds an AI Approval Agent — an internal specialist that generates structured, auditable Accredited Investor (AI) eligibility assessment memos for RM internal use.

Aureus remains the only user-facing assistant. The AI Approval Agent is not exposed directly.

---

## Eligibility Criteria (any one qualifies)

| Criterion | Threshold | Field |
|-----------|-----------|-------|
| Annual Income | ≥ SGD 300,000 | `annual_income` (must be SGD) |
| Net Personal Assets | ≥ SGD 2,000,000 | `net_assets` or `total_assets - total_liabilities` |
| Net Financial Assets | ≥ SGD 1,000,000 | `total_financial_assets` |

All values must be in SGD. If `income_currency` is not SGD, the assessment is blocked with an explicit flag — no FX conversion is performed.

---

## Command

```
/ai_assessment [client name]
/ai_assessment [client name] [1|2|3|4|income|net assets|financial assets]
```

**Natural language equivalents:**
- `accredited investor assessment for John Tan`
- `AI eligibility check for John Tan`
- `does John Tan qualify as accredited?`
- `AI approval for John Tan financial assets`

**If no criteria provided:** Aureus asks the RM to specify:

```
Which eligibility basis should I assess for John Tan?

1️⃣  Income ≥ SGD 300,000
2️⃣  Net Personal Assets ≥ SGD 2,000,000
3️⃣  Net Financial Assets ≥ SGD 1,000,000
4️⃣  Let Aureus evaluate all paths

Reply with 1, 2, 3, or 4
```

The RM can reply with a number or free text — both are normalised to the same internal enum.

---

## Assessment Logic

### Step 1: Load data

Data is loaded from the `AI_Assessment` Google Sheets tab for the requested client. Falls back to mock data in development mode.

### Step 2: Determine eligibility path

- If `ai_selected_criteria` is populated in the sheet → use that path
- If the RM specifies criteria in the command → use that path
- If neither → evaluate all 3 paths, pick the strongest qualifying one

### Step 3: Validation checks

| Check | What it catches |
|-------|----------------|
| Missing critical field | `annual_income`, `total_financial_assets`, `net_assets` absent |
| Missing supporting fields | `income_year`, `employer_name`, `cash_holdings` etc — reduces confidence |
| Currency mismatch | `income_currency != SGD` → blocks income path |
| Negative values | Negative `net_assets` or `total_financial_assets` flagged |
| Net assets inconsistency | Stored `net_assets` ≠ `total_assets - total_liabilities` (>SGD 1 tolerance) |
| Financial assets inconsistency | `total_financial_assets` ≠ sum of components (>SGD 100 tolerance) |

### Step 4: Confidence scoring

| Level | Conditions |
|-------|-----------|
| **High** | Eligible, value clearly above threshold (>10%), no inconsistencies, no missing fields |
| **Medium** | Eligible and qualifies, but some supporting fields missing |
| **Low** | Any inconsistency, currency blocked, missing critical field, or borderline value (within 10% of threshold) |

### Step 5: Generate structured memo

Claude renders the assessment result into a formal compliance memo using a strict section structure.

---

## Output Format

```
*Accredited Investor Assessment — {client name}*

*Eligibility Basis*
[criterion and threshold assessed]

*Supporting Data*
[key values with exact SGD figures]

*Validation Notes*
[checks performed; inconsistencies named explicitly]

*Missing Information*
[missing fields listed, or "No missing required fields"]

*Assessment Summary*
✅ QUALIFIES / ❌ DOES NOT QUALIFY / ⚠️ BLOCKED
Confidence: HIGH / MEDIUM / LOW
[1–2 lines of reasoning]

*RM Declaration*
[standard RM responsibility statement]

*Risk Disclosure*
[reduced regulatory safeguards note under SFA]

_For internal RM use only. Not for client distribution without authorised review._
```

---

## Architecture

```
/ai_assessment John Tan 3
        ↓
CommandRouter._ai_assessment(args)
        ↓
  parse name + criteria from args
  load AI_Assessment data from Sheets (or mock)
  run prelim assess() for writeback decision
        ↓
AureusOrchestrator → AIApprovalAgent.generate(ctx)
        ↓
  AIApprovalAgent.assess()   ← deterministic, no Claude
        ↓
  Claude.generate_raw()      ← memo rendering only
        ↓
WritebackService (async)
  - always: log as interaction
  - if missing/inconsistent data: create follow-up task
        ↓
Formatted memo → Telegram
```

The agent has a two-layer design:
- `assess()` — pure Python, deterministic, Claude-free, fully testable
- `generate()` — calls `assess()` internally, then passes the structured result to Claude for memo rendering

---

## Google Sheets: AI_Assessment Tab

Run once to create the tab (idempotent if already exists):

```bash
venv/bin/python scripts/bootstrap_v7_ai_fields.py
```

| Column group | Fields |
|---|---|
| Identifiers | `assessment_id`, `customer_id`, `customer_name` |
| Income | `annual_income`, `income_currency`, `income_year`, `income_source`, `employer_name`, `job_title` |
| Net Assets | `total_assets`, `total_liabilities`, `net_assets`, `property_value`, `financial_assets_networth`, `mortgage_liability` |
| Financial Assets | `total_financial_assets`, `cash_holdings`, `investment_holdings`, `cpf_investment_amount` |
| Metadata | `ai_selected_criteria`, `data_source`, `last_updated` |

`ai_selected_criteria` is optional. If populated (e.g. `income`), it pre-selects the eligibility path and the RM is not prompted to choose.

---

## Tests

41 unit tests covering all eligibility paths, validation checks, confidence scoring, currency blocking, best-path selection, and criteria normalisation.

```bash
venv/bin/python -m pytest tests/test_ai_approval_agent.py -v
```

---

## Current Limitations (Phase 1)

- **Structured data only** — no document parsing; data must be entered manually in `AI_Assessment` tab
- **Single currency** — income and asset values must be in SGD; non-SGD values are blocked, not converted
- **No PDF/OCR** — client payslips, bank statements, CPF statements cannot be ingested yet
- **No audit trail** — assessment is logged as an interaction but not stored as a versioned record
- **Single record per client** — most recent row in `AI_Assessment` is used; no historical comparison

---

## V8 Upgrade Path: Document Ingestion

Phase 2/3 recommendations:

- **PDF ingestion** — parse payslips, bank statements, CPF statements via OCR or PDF extraction
- **Field auto-population** — extract `annual_income`, `total_financial_assets` etc. directly from documents
- **Source attribution** — link each data field to the document it was extracted from
- **Confidence boost** — document-sourced values → higher confidence than RM-entered values
- **Audit record** — store each assessment as a timestamped, versioned record with source documents attached
- **Multi-currency conversion** — integrate FX rates for non-SGD income/asset normalisation
- **Re-assessment alerts** — flag when existing AI status may need review (e.g. 12-month income check)
