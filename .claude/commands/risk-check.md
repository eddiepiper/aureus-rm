# /risk-check [client_name] [ticker]

Identify risk considerations before discussing a stock with a client.

## Purpose

This command runs a pre-conversation risk screen to help an RM identify potential issues before raising a stock in a client context. It is not an investment recommendation or suitability approval. It is a structured check that surfaces portfolio concentration, mandate fit, stock-level risk, and compliance flags in one view.

If any mandate criterion is violated, flag it prominently at the top of the output — not buried in a section.

## Data Retrieval Steps

Execute all of the following tool calls before generating output. Do not skip any step. If any call returns no data, note the gap explicitly — do not infer or substitute.

1. `suitability.get_risk_profile(client_name)` — risk rating, investment mandate, active constraints, exclusion criteria
2. `portfolio.get_holdings(client_name)` — current holdings
3. `portfolio.get_exposure_breakdown(client_name)` — sector and geographic exposure
4. `market.get_company_snapshot(ticker)` — stock overview, sector, geography, volatility characteristics
5. `fundamentals.get_financials(ticker, period="TTM")` — financial profile, balance sheet notes
6. `compliance.check_disclosures(client_name, ticker)` — required compliance checks, restrictions, required approvals
7. `research.search_news(ticker, days=30)` — recent news and events that may affect the risk picture

If the client name or ticker is not recognized, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. Use the section headers exactly as shown below.

If `compliance.check_disclosures` returns any restrictions or required approvals, display a prominent warning block immediately after the document title, before all other sections:

> **COMPLIANCE FLAG:** [description of restriction or required approval] — Do not proceed with client discussion until resolved.

---

## Risk Check: [Ticker] for [Client Name]

---

## Client Mandate Summary

- Risk rating: [value]
- Mandate type: [e.g., balanced growth, capital preservation, income-focused]
- Key constraints: [list from suitability profile]
- Active exclusions: [sector, ESG, geographic, product — or "None on file"]
- Relevant mandate notes: [any constraint that is directly relevant to this ticker]

---

## Concentration Risk

Assess what adding a position in [ticker] would do to the client's portfolio:

- Current exposure to [ticker]: [% of portfolio or "not held"]
- Current exposure to [ticker's sector]: [% of portfolio]
- Current exposure to [ticker's primary geography]: [% of portfolio]
- Post-addition concentration estimate: [if a position size can be inferred or a standard lot assumed, note it — otherwise state "position size not specified; concentration impact depends on allocation"]
- Threshold flags: [note any single-name >10% or sector >30% that would result]

---

## Stock Risk Profile

Factual characterization of the stock's risk attributes:

- Volatility profile: [high / medium / low volatility characterization based on available data]
- Key business risks: [2–3 specific risks inherent to this company or sector]
- Balance sheet notes: [leverage, liquidity, debt maturity — flag if notable]
- Earnings quality notes: [any recurring vs. one-time items, guidance reliability — flag if notable]

Do not soften risk language to make the stock appear more attractive for the client.

---

## Fit Against Mandate

Assess the stock explicitly against each key mandate criterion. Use the format below:

| Mandate Criterion | Assessment | Notes |
|-------------------|------------|-------|
| Risk rating compatibility | Pass / Flag / Fail | |
| Sector exclusion check | Pass / Flag / Fail | |
| Geographic restriction check | Pass / Flag / Fail | |
| ESG screen (if applicable) | Pass / Flag / Fail / N/A | |
| Liquidity requirements | Pass / Flag / Fail | |
| Concentration limits | Pass / Flag / Fail | |

**Pass** = no issue identified
**Flag** = potential concern, warrants discussion before proceeding
**Fail** = mandate criterion is violated — do not proceed without compliance review

If any criterion returns Fail, restate it at the top of the document in the compliance warning block.

---

## Recent Risk Events

1–3 bullets drawn from news (last 30 days) that are specifically relevant to the risk picture for this client-stock combination. Focus on:
- Earnings misses, profit warnings, guidance cuts
- Regulatory or legal developments
- Management changes or strategic shifts
- Macro events materially affecting the stock's sector

If no material events: state "No material risk events identified in the last 30 days."

---

## Compliance Flags

- Output from `compliance.check_disclosures`: [list all flags, restrictions, or required approvals]
- Any ESG or exclusion screen hits
- Any conflicts of interest or material non-public information flags
- Any required approvals before this stock can be discussed with this client

If no flags: state "No compliance flags identified for this client-stock combination."

---

## Suggested RM Approach

Given the risk picture assembled above, provide specific guidance on how the RM should handle this conversation:

- If the stock passes mandate checks: brief note on how to frame the discussion, what risks to surface proactively
- If the stock has flags: how to handle the flagged items — what to discuss, what to defer, what to escalate
- If the stock fails mandate checks: do not recommend proceeding; instead, guide the RM on how to respond if the client raises the stock independently

Keep this section practical and direct. One short paragraph or 3–4 bullets is sufficient.

---

## Behavioral Rules

- This is a pre-conversation risk screen — not an investment recommendation. Never frame the output as a buy or sell signal.
- If any mandate criterion is violated (Fail), flag it prominently at the top of the document — not only in the Fit Against Mandate table.
- Do not soften risk language to make a stock appear more suitable for the client.
- If `compliance.check_disclosures` returns restrictions, surface them immediately in the compliance warning block at the top.
- Do not fabricate data. If any data source is unavailable, note it explicitly in the relevant section.
- Never omit the Compliance Flags section, even if empty.
