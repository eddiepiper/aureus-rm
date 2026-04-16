# /stock-brief [ticker]

Generate a concise stock brief for RM use.

## Purpose

This command produces a factual, RM-ready overview of a single stock. It is designed to prepare an RM for a client conversation about a specific name — covering business context, performance, financials, and key narratives. It is not an investment recommendation.

## Data Retrieval Steps

Execute the following tool calls. If any call fails or returns no data, note the gap explicitly in the relevant section — do not estimate or invent data.

1. `market.get_company_snapshot(ticker)` — business overview, market cap, key metrics
2. `market.get_price_history(ticker, period="3m")` and `market.get_price_history(ticker, period="1y")` — performance context
3. `fundamentals.get_financials(ticker, period="TTM")` — trailing twelve months financials
4. `fundamentals.get_estimates(ticker)` — consensus revenue and EPS estimates
5. `research.search_news(ticker, days=30)` — recent developments and news
6. `house_view.get_internal_view(ticker)` — internal house view if available

If the ticker is not recognized, ask the user to confirm before proceeding.

## Output Format

Respond in strict markdown. Use the section headers exactly as shown below. Clearly label facts vs. interpretation throughout.

---

## Business Overview

2–3 sentences covering: what the company does, its market position, and its primary revenue drivers. Factual only — no forward-looking interpretation here.

---

## Recent Performance

- 3-month return: [value] vs. [relevant benchmark or sector index]
- 1-year return: [value] vs. [relevant benchmark or sector index]
- YTD return: [value] if calculable from available data
- Note any major inflection points in the price history (significant drawdowns, rallies) with brief context.

If benchmark data is not available, note that comparisons are on an absolute basis only.

---

## Key Financials

Present as a table using last reported figures (TTM where applicable):

| Metric | Value |
|--------|-------|
| Revenue (TTM) | |
| EBITDA Margin | |
| EPS (TTM) | |
| P/E Ratio | |
| P/B Ratio | |
| ROE | |

Mark any unavailable fields as "N/A — not available from source."

---

## Analyst Expectations

Consensus estimates for:
- Next quarter: Revenue estimate, EPS estimate
- Full year: Revenue estimate, EPS estimate

If estimates are not available, state: "Consensus estimates not available from source." Do not invent or interpolate figures.

---

## Key Catalysts

2–4 bullets: specific, near-term factors that could drive upside. Label as interpretation, not fact. Examples: upcoming product launch, regulatory approval, earnings recovery, margin expansion thesis.

---

## Key Risks

2–4 bullets: specific factors that could drive downside or increase uncertainty. Be direct. Do not soften risk language to make the stock appear more attractive.

---

## What Changed Recently

1–2 bullets drawn from news and earnings data (last 30 days). Focus on what is meaningfully new vs. prior narrative — not just a news headline recap.

---

## Internal House View

If `house_view.get_internal_view` returns data: present the internal view here, clearly labeled as **[Internal View — Not for Client Distribution]** unless the RM's workflow explicitly permits sharing.

If no data is returned: state "No internal house view on file."

---

## RM Framing Note

One sentence only: how an RM might introduce this stock in a client conversation in a way that is natural, relevant, and suitability-appropriate. This is a framing suggestion, not a scripted pitch.

---

## Behavioral Rules

- Separate facts from interpretation. Label clearly using terms like "[Fact]" or "[Interpretation]" where the distinction matters.
- Never use language such as "will go up," "guaranteed return," or "risk-free."
- If house view is not available, state "No internal house view on file." — do not omit the section.
- If estimates are unavailable, note it explicitly rather than inventing or rounding from historical data.
- This brief is for RM preparation only — it is not a client-facing document and must not be presented as a research report or investment recommendation.
