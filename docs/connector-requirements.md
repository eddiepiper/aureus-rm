# Aureus RM Copilot — Connector Requirements

Each connector maps to one or more MCP tools in `.mcp.json`. All connectors are currently placeholder stubs. This document specifies what each connector must provide for the system to function.

---

## 1. CRM — Client Profile

**Tool:** `crm.get_client_profile` | **Priority:** P1

**Why needed:** Every client-specific command begins here. Without it, no output can be personalized.

**Commands:** `/client-review`, `/meeting-pack`, `/portfolio-fit`, `/next-best-action`, `/risk-check`

**Input:** `{ "client_id": "string (preferred)", "client_name": "string (fallback)" }`

**Minimum viable output fields:**

| Field | Type | Notes |
|-------|------|-------|
| `client_id` | string | Primary key |
| `name` | string | Full display name |
| `segment` | enum | HNW / UHNW / Mass Affluent / Institutional |
| `rm_owner` | string | Assigned RM name or ID |
| `relationship_since` | date | ISO 8601 |
| `aum_band` | enum | <1M / 1M–5M / 5M–25M / 25M–100M / >100M (SGD) |

**Data freshness:** Real-time or same-day cache.
**Auth pattern:** OAuth2 client credentials or internal API key (TBD with IT).

---

## 2. CRM — Interaction History

**Tool:** `crm.get_recent_interactions` | **Priority:** P1

**Why needed:** Required for meeting prep, follow-up surfacing, and next-best-action context.

**Commands:** `/client-review`, `/meeting-pack`, `/next-best-action`

**Input:** `{ "client_id": "string", "limit": "integer (default: 5)" }`

**Minimum viable output (per item):**

| Field | Type | Notes |
|-------|------|-------|
| `date` | date | ISO 8601 |
| `channel` | string | Call / Email / Meeting / Branch Visit |
| `summary` | string | Max 500 chars |
| `follow_up_pending` | boolean | |
| `follow_up_description` | string | Optional |

**Data freshness:** Real-time.

---

## 3. Portfolio — Holdings

**Tool:** `portfolio.get_holdings` | **Priority:** P1

**Why needed:** Required for all portfolio analysis commands.

**Commands:** `/client-review`, `/portfolio-fit`, `/meeting-pack`, `/next-best-action`, `/risk-check`

**Input:** `{ "client_id": "string" }`

**Minimum viable output (per holding):**

| Field | Type | Notes |
|-------|------|-------|
| `ticker` | string | Exchange-qualified preferred (e.g. D05.SI) |
| `name` | string | Company display name |
| `sector` | string | GICS sector preferred |
| `market_value` | number | In portfolio currency |
| `weight_pct` | number | % of total portfolio |
| `unrealized_pnl_pct` | number | Optional but valuable |

**Portfolio-level:** `total_aum`, `currency`, `as_of_date`

**Data freshness:** End-of-day minimum. Real-time preferred.

---

## 4. Portfolio — Exposure Breakdown

**Tool:** `portfolio.get_exposure_breakdown` | **Priority:** P1

**Why needed:** Concentration checks require aggregated sector/geography/asset class breakdown.

**Commands:** `/portfolio-fit`, `/risk-check`, `/client-review`

**Input:** `{ "client_id": "string" }`

**Minimum viable output:**
- `by_sector`: `{sector_name: weight_pct}`
- `by_geography`: `{country_or_region: weight_pct}`
- `by_asset_class`: `{asset_class: weight_pct}`

---

## 5. Suitability — Risk Profile

**Tool:** `suitability.get_risk_profile` | **Priority:** P1

**Why needed:** All mandate checks and suitability guardrails depend on this.

**Commands:** `/portfolio-fit`, `/risk-check`, `/next-best-action`, `/client-review`

**Input:** `{ "client_id": "string" }`

**Minimum viable output:**

| Field | Type | Notes |
|-------|------|-------|
| `risk_rating` | enum | conservative / moderate / balanced / growth / aggressive |
| `investment_horizon` | string | e.g. "3–5 years" |
| `excluded_sectors` | array | |
| `excluded_geographies` | array | |
| `max_single_name_pct` | number | Hard limit |
| `max_sector_pct` | number | Hard limit |
| `liquidity_requirement` | string | |
| `last_review_date` | date | Flag if > 12 months old |

---

## 6. Suitability — Recommendation Validation

**Tool:** `suitability.validate_recommendation_framing` | **Priority:** P2

**Why needed:** Live compliance validation of generated output language. Supplements `pre_response_guardrail.py` in Phase 3.

**Commands:** All (via hook pipeline)

**Input:** `{ "text": "string", "context": "string (optional)" }`

**Output:** `{ "passed": bool, "flags": [{pattern, location, severity}] }`

**Note:** `pre_response_guardrail.py` serves this function in Phase 1–2.

---

## 7. Market — Company Snapshot

**Tool:** `market.get_company_snapshot` | **Priority:** P2

**Why needed:** Business description, sector, and market cap required for all stock-level outputs.

**Commands:** `/stock-brief`, `/portfolio-fit`, `/compare-stocks`, `/risk-check`

**Input:** `{ "ticker": "string" }`

**Minimum viable output:**

| Field | Type |
|-------|------|
| `name` | string |
| `description` | string (2–4 sentences) |
| `sector` | string |
| `industry` | string |
| `market_cap` | number |
| `exchange` | string |
| `currency` | string |

**Suggested providers:** Bloomberg, Refinitiv Eikon, FactSet.

---

## 8. Market — Price History

**Tool:** `market.get_price_history` | **Priority:** P2

**Why needed:** 3m, 1y, YTD performance context for stock briefs and comparisons.

**Input:** `{ "ticker": "string", "period": "1m|3m|6m|1y|3y" }`

**Output:** Array of `{date, close_price, volume}` — OHLCV preferred.

---

## 9. Fundamentals — Financial Data

**Tool:** `fundamentals.get_financials` | **Priority:** P2

**Why needed:** Revenue, margins, EPS, and balance sheet required for stock briefs and portfolio fit.

**Input:** `{ "ticker": "string", "period": "annual|ttm|quarterly" }`

**Minimum viable output fields:** `revenue`, `gross_margin_pct`, `ebitda_margin_pct`, `net_income`, `eps`, `pe_ratio`, `pb_ratio`, `roe_pct`, `net_debt`, `dividend_yield_pct`

---

## 10. Fundamentals — Analyst Estimates

**Tool:** `fundamentals.get_estimates` | **Priority:** P2

**Why needed:** Consensus estimates required for stock briefs and earnings beat/miss comparisons.

**Input:** `{ "ticker": "string" }`

**Output:** `revenue_next_fy`, `eps_next_fy`, `consensus_rating`, `num_analysts`, `price_target_low`, `price_target_high`, `price_target_median`

---

## 11. Research — Earnings Summary

**Tool:** `research.get_earnings_summary` | **Priority:** P2

**Why needed:** Required for `/earnings-update`.

**Input:** `{ "ticker": "string", "quarter": "string" }`

**Output:** `headline_revenue`, `headline_eps`, `consensus_revenue`, `consensus_eps`, `beat_miss_revenue`, `beat_miss_eps`, `guidance_summary`, `management_tone`, `report_date`

---

## 12. Research — News Search

**Tool:** `research.search_news` | **Priority:** P2

**Why needed:** Recent news context for stock briefs, meeting packs, earnings updates.

**Input:** `{ "ticker": "string", "days_back": "integer (default: 30)" }`

**Output (per article):** `date`, `headline`, `source`, `url` (optional), `relevance_score`

**Suggested providers:** Refinitiv News, Bloomberg News API, Factiva.

---

## 13. House View — Internal View

**Tool:** `house_view.get_internal_view` | **Priority:** P3

**Why needed:** Enriches stock briefs and portfolio fit with proprietary research context.

**Input:** `{ "ticker": "string (optional)", "sector": "string (optional)" }`

**Output:** `available` (bool), `rating` (Overweight/Neutral/Underweight), `summary`, `key_thesis`, `key_risks`, `last_updated`

**Data freshness:** Flag as stale if > 60 days.

---

## 14. Compliance — Disclosures Check

**Tool:** `compliance.check_disclosures` | **Priority:** P3

**Why needed:** Required for `/risk-check` and any command surfacing compliance flags.

**Input:** `{ "ticker": "string", "product_type": "string (optional)" }`

**Output:** `disclosures_required` (bool), `disclosure_list` (array), `distribution_restrictions` (array)

---

## 15. Notes — Save Meeting Prep

**Tool:** `notes.save_meeting_prep` | **Priority:** P3

**Why needed:** CRM write-back for `/meeting-pack` and `/next-best-action` audit trail.

**Input:** `{ "client_id": "string", "meeting_date": "date", "content": "object", "created_by": "string" }`

**Output:** `{ "success": bool, "record_id": "string", "timestamp": "string" }`

**Note:** `crm_logger.py` writes to local JSONL as substitute in Phase 1–2.
