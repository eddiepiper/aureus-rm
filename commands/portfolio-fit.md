# /portfolio-fit [client_name] [ticker]

Evaluate whether a stock is a reasonable fit for the named client's portfolio.

## Purpose

This command helps an RM assess whether a specific stock is suitable to discuss with a named client, given their current portfolio, risk profile, and mandate constraints. It is a portfolio suitability discussion tool — not a buy/sell recommendation.

## Data Retrieval Steps

Execute all of the following tool calls before generating output. Do not skip steps. If any call returns no data, note the gap explicitly — do not infer or substitute.

1. `crm.get_client_profile(client_name)` — segment, AUM band, RM owner, relationship context
2. `suitability.get_risk_profile(client_name)` — risk rating, investment mandate, active constraints, exclusion criteria (sector, ESG, geographic, product type)
3. `portfolio.get_holdings(client_name)` — current holdings
4. `portfolio.get_exposure_breakdown(client_name)` — sector and geographic exposure breakdown
5. `market.get_company_snapshot(ticker)` — stock overview, sector, geography, market cap
6. `fundamentals.get_financials(ticker, period="TTM")` — financial profile of the stock
7. `compliance.check_disclosures(client_name, ticker)` — required compliance checks and any restrictions
8. `house_view.get_internal_view(ticker)` — internal view if available

If the client name or ticker is not recognized, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. Use the section headers exactly as shown below.

---

## Client Portfolio Context

- AUM band: [value or "not disclosed"]
- Risk rating: [value]
- Key mandate constraints: [list constraints from suitability profile]
- Active exclusions: [sector exclusions, ESG screens, geographic restrictions, product restrictions — or "None on file"]
- Relevant notes from CRM profile: [any context that affects suitability assessment]

---

## Current Exposure

- Current exposure to [ticker]: [% of portfolio or "not held"]
- Current exposure to [ticker's sector]: [% of portfolio]
- Current exposure to [ticker's primary geography]: [% of portfolio]
- Overlapping holdings: [any existing positions in the same sector, geography, or with correlated risk profile]

---

## Concentration Impact

State explicitly what adding a position in [ticker] would do to the client's portfolio concentration:
- Impact on single-name concentration
- Impact on sector concentration
- Impact on geographic concentration
- Any threshold breaches (e.g., single name >10%, sector >30%) that would result from adding this position

---

## Diversification Assessment

Does adding this stock improve or reduce portfolio diversification? Assess based on:
- Correlation with existing holdings
- Sector and geographic overlap
- Balance sheet and risk profile relative to existing positions

State clearly: **Adds diversification / Neutral / Reduces diversification** with a one-sentence rationale.

---

## Fit Assessment

State one of the following, in bold, followed by a structured rationale:

**Fits** — stock is consistent with client mandate, adds appropriate exposure, no constraint violations

**Partially Fits** — stock is broadly suitable but has specific considerations the RM should discuss with the client (e.g., size, liquidity, concentration)

**Does Not Fit** — stock violates one or more mandate constraints, exclusion criteria, or would create suitability issues

The rationale must reference the client's risk profile and mandate explicitly. Do not frame this as a buy or sell recommendation.

---

## Suitability Framing

Provide compliant language the RM can use when discussing this stock with the client. This should be:
- Grounded in the client's stated objectives
- Free of performance guarantees or misleading framing
- Appropriate given the Fit Assessment above

If the Fit Assessment is "Does Not Fit," the suitability framing should explain how the RM should handle the conversation if the client raises the stock independently.

---

## Risks to Discuss

2–3 key risks that are specifically relevant to this client given their portfolio and mandate — not generic stock risks. For example: liquidity risk for a client with concentrated illiquid holdings, currency risk for a client with restricted FX exposure, sector concentration for a client already overweight that sector.

---

## Compliance Notes

- Output from `compliance.check_disclosures`: [list any required disclosures, restrictions, or required approvals]
- Any ESG or exclusion screen hits
- Any conflicts of interest or material non-public information flags
- If no flags: state "No compliance flags identified for this client-stock combination."

---

## Behavioral Rules

- The Fit Assessment is a portfolio suitability discussion tool — it is not a buy or sell recommendation. Never frame it as one.
- Always reference the client's risk profile explicitly when assessing fit.
- Do not override suitability constraints even if the stock appears financially attractive.
- If the client has active exclusion criteria (sector, ESG, geographic, product type), check the stock against each criterion and flag any hits immediately.
- If `compliance.check_disclosures` returns restrictions, surface them at the top of the Compliance Notes section.
- If data is unavailable for any step, state so clearly — do not infer suitability from incomplete data.
