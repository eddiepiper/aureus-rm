# /compare-stocks [ticker1] [ticker2]

Compare two stocks to support an RM discussion with a client.

## Purpose

This command produces a structured side-by-side comparison of two stocks for RM use. It is designed to help an RM frame a conversation about relative positioning — for example, when a client asks about switching between two names, or wants to understand the differences before making an allocation decision. It is not a recommendation to buy or sell either stock.

## Data Retrieval Steps

Run the following tool calls for both tickers. Execute them in parallel where possible. If data is unavailable for either ticker on any call, note the gap rather than substituting or estimating.

For each of [ticker1] and [ticker2]:
1. `market.get_company_snapshot(ticker)` — business overview, sector, geography, market cap
2. `fundamentals.get_financials(ticker, period="TTM")` — trailing financials
3. `fundamentals.get_estimates(ticker)` — consensus estimates
4. `research.search_news(ticker, days=30)` — recent developments
5. `house_view.get_internal_view(ticker)` — internal house view if available

If either ticker is not recognized, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. Use the section headers exactly as shown below. Where tables are specified, use markdown tables.

---

## Business Model Comparison

Present as a two-column table or parallel bullet structure:

| | [Ticker1] | [Ticker2] |
|---|---|---|
| What they do | | |
| Market position | | |
| Primary revenue drivers | | |
| Sector | | |
| Primary geography | | |

Keep descriptions factual and brief (1–2 sentences per cell).

---

## Financial Comparison

| Metric | [Ticker1] | [Ticker2] |
|--------|-----------|-----------|
| Revenue (TTM) | | |
| Revenue Growth (YoY) | | |
| EBITDA Margin | | |
| EPS (TTM) | | |
| P/E Ratio | | |
| P/B Ratio | | |
| ROE | | |
| Dividend Yield | | |

Mark any unavailable fields as "N/A — not available from source." Do not fabricate or interpolate figures.

---

## Recent Performance

| Period | [Ticker1] | [Ticker2] |
|--------|-----------|-----------|
| 3-month return | | |
| 1-year return | | |
| YTD return | | |

---

## Analyst Expectations

| Estimate | [Ticker1] | [Ticker2] |
|----------|-----------|-----------|
| Next quarter revenue (consensus) | | |
| Next quarter EPS (consensus) | | |
| Full year revenue (consensus) | | |
| Full year EPS (consensus) | | |

If estimates are unavailable for either name, state so — do not leave cells blank without explanation.

---

## Key Differentiators

3–5 bullets covering what meaningfully separates these two names. Focus on structural differences — business model, competitive position, growth profile, capital allocation, risk characteristics — not just surface-level metrics. Label clearly as interpretation where relevant.

---

## Risk Comparison

For each ticker, list 2–3 key distinct risks. Focus on risks that differentiate the two names, not risks common to both (e.g., both exposed to rising rates — note that once and focus on what is stock-specific).

**[Ticker1] key risks:**
- [risk 1]
- [risk 2]

**[Ticker2] key risks:**
- [risk 1]
- [risk 2]

If one stock appears significantly riskier, note this clearly and directly — without hyperbole, but without softening it either.

---

## Client Suitability Contexts

Without referencing any specific client, describe the general client profile that each name would be better suited to — based on risk profile, income vs. growth orientation, liquidity needs, sector preference, or geographic preference.

**[Ticker1] is typically more suitable for:** [profile description]

**[Ticker2] is typically more suitable for:** [profile description]

This section should help an RM self-assess fit before a client conversation. It is not a suitability determination for any specific client — for that, use `/portfolio-fit`.

---

## Internal House View

If `house_view.get_internal_view` returns data for either ticker, present it here clearly labeled as **[Internal View — Not for Client Distribution]** unless the RM's workflow explicitly permits sharing.

If no data is returned for either: state "No internal house view on file for either name."
If available for one only: present the available view and note the absence for the other.

---

## RM Discussion Points

3–5 bullets to guide the client conversation. These should frame the comparison in a way that is natural and useful for an RM — highlighting the key decision points a client would likely want to understand without steering them toward a predetermined conclusion.

---

## Behavioral Rules

- Do not declare a winner or recommend one stock over the other. Frame the output as supporting an informed discussion.
- Keep suitability language careful and relative — never absolute. Avoid phrases like "clearly superior" or "obviously better."
- If one stock is significantly riskier, note it plainly and specifically — do not obscure it in balanced language.
- Never fabricate financial data. If unavailable, mark as "N/A — not available from source."
- This output is for RM preparation only — it is not a client-facing research document and must not be presented as a research report or investment recommendation.
