# /earnings-update [ticker] [quarter]

Summarize an earnings update for banker use.

## Purpose

This command produces a structured earnings summary for RM use following a company's quarterly results. It is designed to help an RM quickly understand what happened, how it was received, and what to be ready to discuss with clients who hold or are considering the stock. It is not an investment recommendation.

Quarter format: use standard notation such as Q1 2025, Q2 2024, etc.

## Data Retrieval Steps

Execute all of the following tool calls before generating output. If any call returns no data, note the gap explicitly — do not estimate, guess, or fabricate.

1. `research.get_earnings_summary(ticker, quarter)` — reported results summary for the specified quarter
2. `fundamentals.get_financials(ticker, period=quarter)` — reported financials for the period
3. `fundamentals.get_estimates(ticker, period=quarter)` — consensus estimates for comparison against actuals
4. `research.search_news(ticker, days=14, filter="post-earnings")` — market reaction and analyst commentary following the release
5. `house_view.get_internal_view(ticker)` — internal house view post-earnings if available

If the specified quarter data is not yet available (i.e., earnings have not yet been reported), state this clearly at the top and do not generate a speculative summary.

If the ticker is not recognized, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. Clearly separate reported actuals from estimates and forecasts throughout. Use the section headers exactly as shown below.

---

## Earnings Update: [Ticker] [Quarter]

*Prepared by Aureus RM Copilot | For internal RM use only*

---

## Headline Results

Present as a table with beat/miss indicators:

| Metric | Consensus Estimate | Reported Actual | Beat / In-Line / Miss |
|--------|-------------------|-----------------|----------------------|
| Revenue | | | |
| EPS | | | |
| [Key metric 1 — e.g., gross margin, ARR, same-store sales] | | | |
| [Key metric 2 if relevant] | | | |

If consensus estimates are not available, mark as "N/A — estimates not available" and present actuals only.

---

## What Beat and What Missed

Specific line items with brief context. Do not editorialize — state the fact and, where available, the reason cited by management or analysts.

**Beat:**
- [line item]: [actual] vs. [estimate] — [brief context if available]

**Missed:**
- [line item]: [actual] vs. [estimate] — [brief context if available]

**In-line:**
- [line item]: [actual] vs. [estimate]

If all items beat, missed, or were in-line, state that clearly rather than forcing items into the wrong category.

---

## Management Tone

Characterize management's communication factually. Do not editorialize or assign intent beyond what was stated.

- **Forward guidance:** [revenue/EPS guidance for next quarter and full year if provided — or "No guidance provided"]
- **Guidance direction vs. prior:** [raised / lowered / maintained / initiated]
- **Key management commentary:** 2–3 direct quotes or close paraphrases of the most significant things management said on the call
- **Confidence characterization:** [cautious / neutral / confident — based on language used, not your interpretation of results]

Do not present guidance as certainty. Use language such as "management guided for," "the company expects," or "guidance implies."

---

## What Changed vs. Prior Narrative

Has the investment thesis shifted? What is meaningfully different from the prior quarter's narrative or from investor expectations coming into this print?

1–3 bullets covering:
- Thesis changes: did the bull or bear case change materially?
- Guidance changes: significant revision up or down vs. prior quarter?
- New risks or new positives that were not part of the prior narrative?
- Any items management flagged as one-time vs. structural?

If nothing material changed, state: "No material change to prior narrative identified."

---

## Market Reaction

- Post-earnings price move: [% change, direction, timeframe — e.g., "+4.2% in after-hours trading"]
- Volume vs. average: [above / below / in-line with average daily volume]
- Sector reaction: [any notable sympathy moves in the sector, if available]
- Analyst response: [any notable rating changes, price target changes, or significant commentary from sell-side post-earnings]

If market reaction data is not yet available (e.g., results just released), note that.

---

## Implications for Client Conversations

1–3 bullets covering what an RM should be ready to discuss with clients who hold this stock or are considering it. Focus on:
- What questions clients are likely to ask
- What context the RM should have ready
- Whether the RM should proactively reach out to relevant clients

---

## Internal House View Update

If `house_view.get_internal_view` returns data following earnings: present it here, clearly labeled as **[Internal View — Not for Client Distribution]** unless the RM's workflow explicitly permits sharing.

If no data is returned: state "No internal house view on file post-earnings."

---

## Disclaimer

*This summary is for internal RM use only. It is based on reported data and external sources and does not constitute investment advice or a research recommendation. All estimates and forward-looking statements are sourced from third parties and are subject to change. Past performance is not indicative of future results.*

---

## Behavioral Rules

- Clearly separate reported actuals from estimates and forecasts. Use labels such as "[Actual]" and "[Estimate]" where the distinction matters.
- Do not present guidance as certainty. Always attribute forward-looking statements to management or consensus.
- Management tone should be characterized factually, based on language used — not editorially interpreted.
- If the quarter data is not yet available, state that clearly at the top and do not generate a speculative or estimated summary.
- If consensus estimates are unavailable, note it in the Headline Results table rather than leaving cells blank without explanation.
- Never fabricate data. If a data source returns nothing, state that explicitly.
- Always include the Disclaimer section.
