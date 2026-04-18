# AI Assessment — Business Rules Reference

**Applies to:** V7 `AIApprovalAgent` | Singapore Accredited Investor (AI) eligibility  
**Status:** Phase 1 — structured data only; document ingestion is out of scope

---

## Scope

This document covers the business rules, field definitions, status codes, and confidence scoring logic for the V7 AI Approval Agent. It is the authoritative reference for anyone reading, modifying, or testing `services/ai_approval_agent.py`.

This is **not** a user-facing guide. It is an internal compliance and engineering reference.

---

## Locked Rules

The following rules are non-negotiable. They are not configurable and must not be altered without a compliance-approved change:

1. **Single-criterion assessment only** — the engine evaluates exactly the criterion selected by the RM. No auto-switching.
2. **No auto-switching** — if the selected criterion fails, the result is `not_eligible` for that criterion. The engine does not evaluate or suggest an alternative.
3. **External manual values require evidence** — values where `source_is_internal = False` and `evidence_type` is absent, or `evidence_date` is stale, are excluded from `recognised_amount`. They cannot support a pass.
4. **Internal bank-held values** — where `source_is_internal = True`, the engine accepts the value without requiring separate evidence documents.
5. **Primary residence capped at SGD 1,000,000** — net equity (FMV × ownership_share − secured_loan × ownership_share) is capped regardless of actual value.
6. **CPFIS only** — only CPFIS-eligible investments are included in NFA. Raw CPF balances (OA, SA, MA) are explicitly excluded.
7. **DPT/stablecoin excluded** — digital payment tokens and stablecoins are not in the schema and must not be referenced.
8. **Borderline band: 10% above threshold** — a recognised amount in the range (threshold, threshold × 1.10] is treated as borderline and forces `manual_review`, regardless of other clean conditions. Confidence is capped at Medium.
9. **Joint account: flag only** — `joint_account_flag = True` is recorded. No separate qualification path for jointly-held assets in Phase 1. `ownership_share_pct` is applied to primary residence and other real estate if provided.
10. **Opt-in is out of scope** — AI opt-in/opt-out decisions are not generated, referenced, or handled.
11. **Draft only** — all outputs are drafts for checker review. The checker confirms or rejects. The engine never produces a final AI determination.
12. **Checker confirms** — `checker_status` is always `pending_review` at output time. The checker updates this field externally.

---

## Eligibility Criteria and Thresholds

| Criterion Key | Display Label | SGD Threshold | Rule |
|---|---|---|---|
| `income` | Annual Income | ≥ 300,000 | Preceding 12-month income from employment/business, supported by acceptable evidence |
| `net_personal_assets` | Net Personal Assets | > 2,000,000 | Total assets less total liabilities, using explicit field formula; primary residence capped at SGD 1M |
| `financial_assets` | Net Financial Assets | > 1,000,000 | Deposits + eligible investments + CPFIS − related liabilities; raw CPF excluded |

---

## Assessment Status Codes

| Code | Meaning | When assigned |
|---|---|---|
| `eligible` | Client meets threshold under selected criterion | Pass, no issues, confidence ≥ Medium |
| `not_eligible` | Client does not meet threshold | Recognised amount below threshold |
| `pending_info` | Assessment cannot be completed | Critical field missing or external value unsupported |
| `manual_review` | Pass but checker must review before finalising | Borderline value, stale evidence, inconsistency flags, or unsupported data |

---

## Confidence Levels

| Level | Conditions |
|---|---|
| `High` | Eligible; no inconsistency flags; no missing fields; no manual review reasons |
| `Medium` | Eligible; manual review required but no inconsistency flags or missing critical fields |
| `Low` | Any of: not eligible, pending info, inconsistency flags present, borderline with missing fields |

Borderline values (within 10% above threshold) always cap confidence at Medium.

---

## Source Control Gate

The engine applies a source control gate before accepting any value toward `recognised_amount`:

| Condition | Result |
|---|---|
| `source_is_internal = True` | Value accepted; no evidence required |
| `source_is_internal = False` + valid `evidence_type` + non-stale `evidence_date` | Value accepted |
| `source_is_internal = False` + missing `evidence_type` | Value excluded; flag generated; `pending_info` or `manual_review` |
| `source_is_internal = False` + stale `evidence_date` | Value excluded; flag generated; `manual_review` |

---

## Evidence Recency Limits

| `evidence_type` | Max age (days) | Notes |
|---|---|---|
| `income_statement` | 60 | Primary basis for income criterion |
| `employer_letter` | 60 | Alternative income basis |
| `external_investment_statement` | 60 | NFA component basis |
| `letter_of_financial_standing` | 90 | NPA alternative basis |
| `property_valuation` | 365 | Primary residence valuation |
| `noa` | Supplementary | Not sufficient as sole primary basis |

Evidence more than the stated days old is stale → forces `manual_review`, reduces confidence.

---

## Field Dictionary — Income Criterion

| Field | Type | Required | Notes |
|---|---|---|---|
| `annual_income` | float (SGD) | Critical | Absent → `pending_info` |
| `income_currency` | string | Recommended | Defaults to SGD if absent; non-SGD requires `fx_rate_used` |
| `fx_rate_used` | float | Required if non-SGD | Absent for non-SGD → value excluded |
| `fx_rate_date` | date string | Recommended | Absent for non-SGD → flag (FX basis unverifiable) |
| `income_period_start` | date string | Required | Absent → `missing_fields` + `manual_review` |
| `income_period_end` | date string | Required | Absent → `missing_fields` + `manual_review` |
| `source_is_internal` | bool | Required | False with no evidence → value excluded |
| `evidence_type` | string | Required if external | See recency table above |
| `evidence_date` | date string | Required if external | Stale → `manual_review` |
| `latest_noa_year` | string | Supplementary | Noted in audit trail; not primary basis |
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
| **DEPRECATED** | | | |
| `net_assets` | float | Backward-read | Used as legacy fallback if all new fields absent |
| `total_assets` | float | Backward-read | Used with `total_liabilities` as secondary fallback |
| `total_liabilities` | float | Backward-read | |
| `property_value` | float | Backward-read | Replaced by `primary_residence_fmv` |
| `mortgage_liability` | float | Backward-read | Replaced by `primary_residence_secured_loan` |
| `financial_assets_networth` | float | Backward-read | Replaced by `financial_assets_for_npa_value` |

**NPA computation formula:**
```
pr_equity             = max(0, primary_residence_fmv × ownership_share_pct
                              − primary_residence_secured_loan × ownership_share_pct)
recognised_pr         = min(pr_equity, 1_000_000)
other_re_equity       = max(0, (other_real_estate_value − other_real_estate_secured_loans)
                              × ownership_share_pct)
recognised_npa        = other_personal_assets_value
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
| `cpf_investment_amount` | float | Optional | CPFIS only — NOT raw CPF balances |
| `total_financial_assets` | float | Fallback | Used only if no component breakdown |
| `financial_assets_related_liabilities` | float | Optional | Aggregate; overrides sum of margin + credit if provided |
| `margin_loan_balance` | float | Optional | Deducted from NFA |
| `portfolio_credit_line_balance` | float | Optional | Deducted from NFA |
| `statement_date` | date string | Recommended if external | Evidence recency check |
| `source_is_internal` | bool | Required | Governs all asset values |

**NFA computation formula:**
```
component_sum   = cash_holdings
                  + investment_holdings
                  + funds_under_management_value
                  + cpf_investment_amount        # CPFIS only
total_liab      = financial_assets_related_liabilities  # if provided
               OR margin_loan_balance + portfolio_credit_line_balance
recognised_nfa  = component_sum − total_liab
```

**Explicit exclusions (hard-coded):**
- Raw CPF balances (OA, SA, MA, RA)
- DPT / stablecoin values
- Non-financial assets

---

## Decision Output Fields (written back to AI_Assessment tab)

| Field | Type | Written by |
|---|---|---|
| `selected_criterion` | string | Engine |
| `recognised_amount_sgd` | float | Engine |
| `threshold_sgd` | float | Engine |
| `pass_result` | bool | Engine |
| `confidence_level` | string | Engine |
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

## Architecture Decision Notes

**Why two `assess()` calls per command invocation:**
`CommandRouter._ai_assessment()` calls `assess()` before `generate()` to determine writeback decisions (create follow-up task or not). `generate()` calls `assess()` again internally. This is intentional — the deterministic layer is fast (no I/O, no Claude), and running it twice ensures the writeback decision is made on the same logic that drives the memo. The alternative (passing the prelim result into generate()) would couple the two layers unnecessarily.

**Why Claude cannot alter the decision:**
The structured `AIDecisionResult` is passed to Claude as fixed inputs in the memo prompt. The system prompt explicitly prohibits Claude from rounding, altering, or softening any decision field. Claude's role is rendering prose — not reasoning about eligibility.

**Why the primary residence is capped:**
MAS AI eligibility guidelines for the net personal assets criterion exclude the net value of primary residence from the computation. The cap of SGD 1,000,000 is a regulatory policy parameter defined in `AI_ASSESSMENT_POLICY`, not a business choice.

**Why source control excludes external manual values without evidence:**
An RM-entered figure with no documentary basis cannot be audited or verified. Accepting it would undermine the defensibility of the assessment. Only bank-held values (directly verifiable) or external values with valid, dated, non-stale evidence documents can support a pass.

---

## What Is Out of Scope (Phase 1)

| Topic | Status |
|---|---|
| PDF/OCR ingestion of payslips, bank statements, CPF statements | Deferred — Phase 2/3 |
| Multi-currency auto-conversion | Deferred — manual FX rate entry supported |
| Versioned audit trail per assessment | Deferred — interaction log only |
| Historical comparison (re-assessment) | Deferred |
| Re-assessment alerts (12-month income check) | Deferred |
| Opt-in / opt-out workflow | Out of scope |
| DPT / stablecoin handling | Excluded by design |
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
2. Checker reviews the memo in the `AI_Assessment` tab (`memo_text` column)
3. Checker updates `checker_status` (`approved` / `rejected`) and adds `assessor_notes`
4. RM obtains client signature on AI declaration form before any reclassification
