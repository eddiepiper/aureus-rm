# AI Assessment — Business Rules Reference

**Applies to:** V7 `AIApprovalAgent` | Singapore Accredited Investor (AI) eligibility  
**Status:** Phase 1 — structured data only; document ingestion is out of scope

---

## Scope

This document covers the assessment logic, field definitions, status codes, and governance controls for the V7 AI Approval Agent. It is the authoritative reference for anyone reading, modifying, or testing `services/ai_approval_agent.py`.

This document separates two distinct layers:

- **Section A — Regulatory eligibility logic**: the legal threshold framework under the Securities and Futures Act (Cap. 289) and MAS Notice SFA 04-N12. This is what determines whether a client meets the AI definition.
- **Section B — Internal bank policy overlays**: operational, evidentiary, and governance controls applied by the bank on top of the regulatory framework. These are not MAS-mandated. They should be treated as bank policy, reviewed by Compliance/Legal, and clearly labelled as such in any client-facing or audit-facing output.

This is **not** a user-facing guide. It is an internal compliance and engineering reference.

---

## Section A — Regulatory Eligibility Logic

### A1. Eligibility Criteria

An individual qualifies as an Accredited Investor in Singapore if they meet **at least one** of the following criteria under the SFA:

| Criterion | Regulatory Definition |
|---|---|
| Annual Income | Income in the **preceding 12 months** is not less than SGD 300,000 (or its equivalent in a foreign currency) |
| Net Personal Assets | Net personal assets exceeding SGD 2,000,000 (or its equivalent in a foreign currency) |
| Net Financial Assets | Net financial assets (investment portfolio + deposits net of related liabilities) exceeding SGD 1,000,000 (or its equivalent in a foreign currency) |

**Note on income wording:** The criterion is "income in the preceding 12 months not less than SGD 300,000" — not generic annual salary. The 12-month period and the "not less than" formulation are the statutory language.

### A2. Primary Residence Treatment in NPA

Under the regulatory framework, the net value of a client's primary residence is recognised in NPA calculation, subject to a cap:

- **Net equity** = fair market value × ownership share − secured loan × ownership share
- **Recognised contribution** = min(net equity, SGD 1,000,000)

This cap is a regulatory policy parameter, not a bank choice.

### A3. Net Financial Assets — Net of Related Liabilities

NFA is assessed **net of related liabilities** — margin loans and portfolio credit lines against the investment portfolio reduce the NFA figure. This is a statutory requirement, not a bank overlay.

### A4. Assessment Output vs. Final Reclassification

The engine produces an **assessment result** — a determination of whether the client's financial data meets the regulatory threshold under the selected criterion. This is **not** a final AI reclassification.

Final treatment as an Accredited Investor requires, in addition:
- Client declaration and opt-in (client must affirmatively elect AI status)
- Checker review and approval
- Signed AI declaration form

The Python engine determines the **assessment result**. The final reclassification outcome requires the human workflow steps above.

---

## Section B — Internal Bank Policy Overlays

The following controls are **bank operating policy**, not statutory MAS requirements. They have been implemented as prudent governance. Each should be reviewed and formally endorsed by Compliance/Legal before being cited in audit or client-facing documentation.

### B1. Single-Criterion Workflow *(Internal Operating Policy)*

The current implementation assesses exactly the criterion selected by the RM. If the selected criterion fails, the result is `not_eligible` for that criterion. The engine does not evaluate or suggest an alternative criterion.

**This is a bank workflow rule, not a legal requirement.** A client may legally qualify under any applicable criterion. This constraint exists for operational consistency and auditability, not because the law prohibits multi-criterion assessment.

If the bank wishes to allow multi-criterion evaluation in future, this rule can be relaxed without changing the regulatory logic.

### B2. Evidence Recency Limits *(Internal Documentary Freshness Policy)*

Evidence older than the following limits is treated as stale and triggers `manual_review`:

| Evidence Type | Bank Policy Limit | Notes |
|---|---|---|
| `income_statement` | 60 days | Primary income basis |
| `employer_letter` | 60 days | Alternative income basis |
| `external_investment_statement` | 60 days | NFA component basis |
| `letter_of_financial_standing` | 90 days | NPA alternative basis |
| `property_valuation` | 365 days | Primary residence valuation |
| `noa` | Supplementary only | See B4 below |

These are **bank-defined freshness rules**, not MAS-mandated time limits. They represent a prudent evidencing standard and should be treated as such in any audit or review context.

### B3. Borderline Band — 10% Above Threshold *(Internal Governance Overlay)*

If a client's recognised amount falls within the range `(threshold, threshold × 1.10]`, the engine:
- Forces status to `manual_review` regardless of other conditions
- Caps confidence at Medium
- Records manual review reason: "Borderline pass — recognised amount within 10% of threshold"

| Criterion | Threshold | Borderline upper |
|---|---|---|
| Income | SGD 300,000 | SGD 330,000 |
| NPA | SGD 2,000,000 | SGD 2,200,000 |
| NFA | SGD 1,000,000 | SGD 1,100,000 |

This is a **bank governance overlay** — an internal quality-control gate. It is not part of the legal eligibility framework. A client at SGD 305,000 income legally meets the criterion; this band exists as a bank policy prudence check requiring human review before proceeding.

### B4. NOA Treatment *(Internal Documentary Sufficiency Policy)*

The Notice of Assessment (NOA) from IRAS is accepted as supplementary context only. It is noted in the audit trail but does not serve as the primary or sole basis for an income assessment pass.

This reflects a **bank documentary sufficiency standard**, not a statutory rule that NOA is legally insufficient. Compliance/Legal should confirm whether NOA alone meets the bank's evidencing standard for this purpose.

### B5. CPF / CPFIS Admissibility *(Internal Asset Admissibility Policy)*

Only CPFIS-eligible investments are included in the NFA computation. Raw CPF balances (OA, SA, MA, RA) are excluded.

This reflects the bank's current **asset admissibility policy**. The rationale is that raw CPF balances are not freely deployable or transferable investment assets. This treatment should be confirmed by Legal/Compliance as consistent with the bank's interpretation of "investment portfolio and deposits" under the SFA definition.

### B6. DPT / Stablecoin Exclusion *(Internal Asset Admissibility Policy)*

Digital payment tokens (DPT) and stablecoins are not included in the schema and are not counted toward any criterion.

This reflects the bank's current **asset admissibility stance** for Phase 1. The regulatory position on DPT classification in NFA/NPA contexts is evolving. This exclusion should be confirmed by Legal as the correct position and revisited as MAS guidance on digital assets develops.

### B7. Fallback to Total Financial Assets *(Operational Fallback — Use With Caution)*

If no component breakdown (cash, investments, CPFIS, liabilities) is available, the engine falls back to a single `total_financial_assets` figure.

**Risk:** This fallback cannot verify that the gross figure is net of related liabilities, or that it excludes non-qualifying assets. A checker should be aware when a fallback figure is in use and should not approve without verifying the composition of the total.

This fallback is **flagged in the output** and should be visible to the checker.

### B8. Confidence Framework *(Internal Workflow Construct)*

The confidence levels (`High`, `Medium`, `Low`) are internal workflow indicators. They are not regulatory determinations and should not be cited as part of the eligibility finding.

| Level | Conditions |
|---|---|
| `High` | Eligible; no inconsistency flags; no missing fields; no manual review reasons |
| `Medium` | Eligible; manual review required but no inconsistency flags or missing critical fields |
| `Low` | Any of: not eligible, pending info, inconsistency flags present, borderline with missing fields |

Borderline values (within 10% above threshold) always cap confidence at Medium per policy in B3.

---

## Architecture Notes

### Why the engine is deterministic (GREEN)

The `AIDecisionResult` is computed entirely in Python before Claude is involved. Claude receives the decision object as fixed inputs and is explicitly prohibited from rounding, softening, or altering any decision field. Claude's role is prose rendering only.

This is the correct pattern for a regulated eligibility workflow: the decision is auditable, reproducible, and not dependent on LLM reasoning.

### Why two `assess()` calls per command invocation

`CommandRouter._ai_assessment()` calls `assess()` before `generate()` to make writeback decisions. `generate()` calls `assess()` again internally. This is intentional — the deterministic layer is fast (no I/O, no Claude), and running it twice ensures the writeback decision is based on the same logic that drives the memo. Coupling the two by passing the prelim result in would be unnecessary.

### Why the primary residence is capped (GREEN)

The SGD 1,000,000 cap on primary residence contribution to NPA is a regulatory policy parameter defined in MAS guidance, not a bank discretionary choice.

### Why source control excludes external manual values without evidence (GREEN)

An RM-entered figure with no documentary basis cannot be audited. Accepting it would undermine the defensibility of the assessment. Only bank-held values (directly verifiable) or external values with valid, dated, non-stale evidence can support a pass.

---

## Assessment Status Codes

| Code | Meaning | When assigned |
|---|---|---|
| `eligible` | Client meets threshold under selected criterion | Pass; confidence ≥ Medium |
| `not_eligible` | Client does not meet threshold | Recognised amount below threshold |
| `pending_info` | Assessment cannot be completed | Critical field missing or external value unsupported |
| `manual_review` | Passes threshold but checker must review before proceeding | Borderline value, stale evidence, inconsistency flags, or unsupported data |

**Note:** `eligible` means the assessment result is a pass under the selected criterion. It does not mean the client has been reclassified as an Accredited Investor. Final treatment still requires the checker workflow and client declaration described in Section A4.

---

## Decision Output Fields (written back to AI_Assessment tab)

| Field | Type | Written by |
|---|---|---|
| `selected_criterion` | string | Engine |
| `recognised_amount_sgd` | float | Engine |
| `threshold_sgd` | float | Engine |
| `pass_result` | bool | Engine |
| `confidence_level` | string | Engine (bank policy construct — see B8) |
| `assessment_status` | string | Engine |
| `missing_fields` | pipe-delimited string | Engine |
| `inconsistency_flags` | pipe-delimited string | Engine |
| `manual_review_required` | bool | Engine |
| `manual_review_reasons` | pipe-delimited string | Engine |
| `joint_account_flag` | bool | Engine (passed through from input) |
| `joint_account_note` | string | Engine (passed through from input) |
| `checker_status` | string | Engine sets `pending_review`; checker updates |
| `memo_text` | string (max 2000 chars) | Engine (full output including summary card) |
| `assessor_notes` | string | Checker fills manually |
| `last_updated` | date string | Engine |

---

## Field Dictionary — Income Criterion

| Field | Type | Required | Notes |
|---|---|---|---|
| `annual_income` | float (SGD) | Critical | Income in preceding 12 months; absent → `pending_info` |
| `income_currency` | string | Recommended | Defaults to SGD if absent; non-SGD requires `fx_rate_used` |
| `fx_rate_used` | float | Required if non-SGD | Absent for non-SGD → value excluded |
| `fx_rate_date` | date string | Recommended | Absent for non-SGD → flag (FX basis unverifiable) |
| `income_period_start` | date string | Required | Must cover preceding 12 months; absent → `missing_fields` + `manual_review` |
| `income_period_end` | date string | Required | Absent → `missing_fields` + `manual_review` |
| `source_is_internal` | bool | Required | False with no evidence → value excluded |
| `evidence_type` | string | Required if external | See Section B2 recency table |
| `evidence_date` | date string | Required if external | Stale → `manual_review` per B2 |
| `latest_noa_year` | string | Supplementary | Noted in audit trail; not primary basis per B4 |
| `latest_noa_amount` | float | Supplementary | Noted; does not replace `annual_income` |

---

## Field Dictionary — Net Personal Assets Criterion

| Field | Type | Required | Notes |
|---|---|---|---|
| `primary_residence_fmv` | float | Preferred | Legacy fallback: `property_value` |
| `primary_residence_secured_loan` | float | Preferred | Legacy fallback: `mortgage_liability` |
| `ownership_share_pct` | float (0–1) | Required if joint | Applied to residence and other real estate |
| `property_valuation_date` | date string | Required | Absent → flag + `manual_review` |
| `other_personal_assets_value` | float | Preferred | External without evidence → excluded |
| `other_real_estate_value` | float | Optional | Equity applied at `ownership_share_pct` |
| `other_real_estate_secured_loans` | float | Required if `other_real_estate_value` | |
| `financial_assets_for_npa_value` | float | Preferred | Not the same as NFA criterion total |
| `insurance_surrender_value` | float | Optional | |
| `business_interest_value` | float | Optional | |
| `other_personal_liabilities_value` | float | Optional | Deducted from NPA total |
| `source_is_internal` | bool | Required | Governs all asset values in this criterion |

**NPA computation formula:**
```
pr_equity        = max(0, primary_residence_fmv × ownership_share_pct
                          − primary_residence_secured_loan × ownership_share_pct)
recognised_pr    = min(pr_equity, 1,000,000)          ← regulatory cap (Section A2)

other_re_equity  = max(0, (other_real_estate_value − other_real_estate_secured_loans)
                          × ownership_share_pct)

recognised_npa   = other_personal_assets_value
                 + other_re_equity
                 + financial_assets_for_npa_value
                 + insurance_surrender_value
                 + business_interest_value
                 + recognised_pr
                 − other_personal_liabilities_value
```

---

## Field Dictionary — Net Financial Assets Criterion

| Field | Type | Required | Notes |
|---|---|---|---|
| `cash_holdings` | float | Preferred component | Deposit account balances |
| `investment_holdings` | float | Preferred component | Investment products held |
| `funds_under_management_value` | float | Optional | ILP / managed fund values |
| `cpf_investment_amount` | float | Optional | CPFIS only — raw CPF balances excluded per B5 |
| `total_financial_assets` | float | Fallback | Used only if no component breakdown — see B7 |
| `financial_assets_related_liabilities` | float | Optional | Aggregate; overrides sum of margin + credit if provided |
| `margin_loan_balance` | float | Optional | Deducted from NFA (statutory requirement) |
| `portfolio_credit_line_balance` | float | Optional | Deducted from NFA (statutory requirement) |
| `statement_date` | date string | Recommended if external | Evidence recency check per B2 |
| `source_is_internal` | bool | Required | Governs all asset values |

**NFA computation formula:**
```
component_sum  = cash_holdings
               + investment_holdings
               + funds_under_management_value
               + cpf_investment_amount        ← CPFIS only (bank policy, see B5)

total_liab     = financial_assets_related_liabilities   (if provided)
              OR margin_loan_balance + portfolio_credit_line_balance

recognised_nfa = component_sum − total_liab   ← net of related liabilities (statutory, see A3)
```

---

## Checker Workflow

1. RM runs `/ai_assessment` → memo delivered via Telegram
2. Checker reviews `memo_text` in the `AI_Assessment` tab
3. Checker updates `checker_status` (`approved` / `rejected`) and adds `assessor_notes`
4. RM obtains client signature on AI declaration form before any reclassification treatment

`checker_status` is always `pending_review` at engine output time. The checker — not the engine — closes the loop.

---

## What Is Out of Scope (Phase 1)

| Topic | Status |
|---|---|
| PDF/OCR ingestion of payslips, bank statements, CPF statements | Deferred — Phase 2/3 |
| Multi-currency auto-conversion | Deferred — manual FX rate entry supported |
| Versioned audit trail per assessment | Deferred |
| Historical comparison / re-assessment | Deferred |
| Re-assessment alerts (12-month income check) | Deferred |
| Opt-in / opt-out workflow | Out of scope (Phase 1) |
| DPT / stablecoin handling | Excluded by bank policy (see B6) — subject to Legal review |
| Joint account separate qualification path | Deferred — flag only in Phase 1 |
| Multiple records per client (beyond most recent) | Deferred |

---

## Operator Notes

**Initial setup:**
```bash
# Create the AI_Assessment tab (idempotent):
venv/bin/python scripts/bootstrap_v7_ai_fields.py
```

**Running assessments:**
- Populate client data in the `AI_Assessment` tab before running `/ai_assessment`
- `source_is_internal = True` for bank-held data; `False` for RM-entered external data
- All amounts in SGD; non-SGD income requires `fx_rate_used` and `fx_rate_date`
- After assessment, decision output fields are written back to the same row automatically

**Checker workflow:**
1. RM runs `/ai_assessment` → memo delivered via Telegram
2. Checker reviews in the `AI_Assessment` tab (`memo_text` column)
3. Checker updates `checker_status` and `assessor_notes`
4. RM obtains client signature before any reclassification
