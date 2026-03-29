# Stock Analysis Framework for RM Use

## Purpose

This skill governs how Claude analyzes individual securities for relationship manager use. The output sits between a Bloomberg terminal printout (too raw) and a retail investor summary (too simplified). The RM needs enough to have an intelligent, client-appropriate conversation — not to publish equity research.

---

## Core Principle

**Start from facts. Derive interpretation. Then frame for conversation.** Never lead with a conclusion. Every interpretive statement must be traceable to a specific data point. Every forward-looking framing must be labeled as such and hedged appropriately.

---

## The Facts → Interpretation → Framing Pipeline

Every stock analysis should move through three distinct layers:

### Layer 1 — Facts (What Is Reported)

The factual record: reported financials, announced events, verified market data. These statements require no hedging — they are what they are.

Examples:
- Revenue grew 14% YoY in Q3 2025
- The company reported a net loss of USD 220M
- Free cash flow turned positive for the first time in three years
- Management guided for flat revenue in Q4 2025

**Rule:** If it is not from a reported source, it is not a fact. Label it accordingly.

### Layer 2 — Interpretation (What the Facts Mean)

Analysis of what reported data suggests about the business — its trajectory, financial health, competitive position, or risk profile. These statements represent analytical judgment and should be clearly distinguished from raw facts.

Examples:
- The margin compression may indicate rising input cost pressure
- The improvement in FCF could suggest the capital-intensive growth phase is moderating
- Declining revenue in the core segment, offset by growth in the new division, suggests a business model in transition

**Rule:** Interpretive statements should not be presented as certain. Use "suggests", "may indicate", "could reflect", "is consistent with".

### Layer 3 — Framing (How to Discuss With a Client)

Translation of interpretation into client-relevant context. This layer answers: "Why does this matter to someone holding this stock?" Framing connects financial data to client outcomes (income, growth, risk exposure).

Examples:
- For an income-oriented client: "The dividend was maintained, though the payout ratio has increased, which may be worth monitoring"
- For a growth-oriented client: "Revenue growth remained above the sector average, though margins narrowed, which is typical in aggressive expansion phases"

**Rule:** Framing is contextual. It depends on the client's goals, mandate, and existing exposure. Reframe accordingly when client context is known.

---

## Key Financial Ratios to Surface

Surface the following ratios where data is available. Always include the unit, the period, and a brief interpretation anchor.

| Ratio | What to Surface | Interpretation Anchor |
|-------|----------------|----------------------|
| **Revenue Growth (YoY)** | % change | Accelerating vs decelerating |
| **Gross Margin** | % | Trending up/down vs sector |
| **Operating Margin / EBIT Margin** | % | Operating leverage signal |
| **Net Income Margin** | % | Bottom-line profitability |
| **EPS (reported vs consensus)** | Value + beat/miss | Earnings quality signal |
| **Free Cash Flow** | Value, positive/negative | Sustainability of operations |
| **Net Debt / EBITDA** | Multiple | Leverage and balance sheet stress |
| **P/E (trailing and forward)** | Multiple | Relative to sector and history |
| **EV/EBITDA** | Multiple | Preferred for capital-intensive firms |
| **Price/Book** | Multiple | Useful for financials |
| **Dividend Yield** | % | Income context |
| **Dividend Coverage / Payout Ratio** | Ratio or % | Dividend sustainability |

**Do not surface all ratios for every stock.** Select those most relevant to the business model and client context. A financial stock analysis should emphasize P/B and ROE; a tech stock analysis should emphasize revenue growth and FCF; an industrial stock analysis should emphasize margins and leverage.

---

## Business Model Key Value Drivers

Adapt the analytical lens based on the sector:

**Financials (banks, insurance, asset managers):**
- Net interest margin, return on equity, loan growth, credit quality, capital ratios

**Technology:**
- Revenue growth rate, gross margin, R&D intensity, recurring revenue mix, FCF conversion

**Consumer (discretionary and staples):**
- Same-store sales growth, brand pricing power, margin trajectory, inventory management

**Industrials / Materials:**
- Volume and pricing trends, input cost exposure, order backlog, capex cycle

**Healthcare:**
- Pipeline strength, patent cliff exposure, regulatory milestones, pricing environment

**Real Estate / Infrastructure:**
- Occupancy, rent growth, FFO/AFFO, leverage, asset quality

---

## Valuation Assessment

Use multiple methods. Do not anchor on a single metric. Acknowledge uncertainty explicitly.

**Methods to reference:**
- **Relative valuation:** P/E, EV/EBITDA, P/B vs sector peers and historical averages
- **Yield-based:** Dividend yield relative to risk-free rate or sector average
- **Analyst consensus:** Range of price targets, median target, implied upside/downside vs current price

**Principles:**
- State whether the stock screens as expensive, in-line, or cheap — relative to what (peers, history, or its own growth rate)
- Do not present a specific price target as a fact without attributing it to an analyst or consensus
- Acknowledge the range of analyst views, not just the median
- When valuation methods conflict, surface the tension rather than resolving it artificially

Example framing: "On a forward P/E basis the stock trades at a discount to its 3-year average, though EV/EBITDA relative to sector peers remains elevated, reflecting differing assumptions about near-term margin recovery."

**Avoid false precision:** Do not calculate implied targets. Do not assign probabilities to outcomes without a stated basis.

---

## Identifying What Changed in the Most Recent Quarter

The most analytically valuable output is the delta vs prior narrative. For each earnings cycle, identify:

- Did the company beat, meet, or miss consensus on revenue and EPS?
- Did management guidance change (raised, maintained, lowered)?
- Did margin trends shift direction?
- Did the key thesis (growth story, turnaround, yield play) advance or stall?
- Were there any one-time items that distort the headline numbers?
- Did management commentary introduce new risks or confirm existing ones?

Frame the change explicitly: "Last quarter, the market concern was X. This quarter's results [support / challenge / do not resolve] that concern because..."

---

## Summarizing Analyst Consensus

When analyst consensus data is available, present it with appropriate calibration:

- State the number of analysts covered and the buy/hold/sell split
- State the median price target and the range (low to high)
- Note whether consensus has moved materially in the last 30–90 days
- Do not imply that consensus is correct or that divergence from consensus is wrong

**Never overstate confidence in consensus.** Analyst consensus reflects a distribution of views at a point in time. It is a data point, not a verdict.

Example: "Of 18 analysts covering the stock, 11 rate it Buy, 5 Hold, and 2 Sell. The median 12-month price target is USD 142, with a range of USD 105 to USD 165. Consensus estimates have been revised upward following the most recent earnings release."

---

## Catalysts and Risks

Present catalysts and risks in a balanced way. Do not lead with either. For each:

**Catalysts** — events or developments that could improve the investment case:
- Label as potential, not certain
- Indicate rough timing where known
- Distinguish between company-specific and macro/sector catalysts

**Risks** — factors that could impair the investment case:
- Include both near-term (next 1–2 quarters) and structural risks
- Be specific — "market risk" is not a useful risk
- Do not list risks for coverage completeness; list them for relevance

**Balance rule:** If there are 4 catalysts and 1 risk, surface the imbalance. Either the risk is underweighted or the catalyst list is padded. Aim for a proportionate picture, not an optimistic one.

---

## Handling Missing or Inconsistent Data

- If a key ratio is unavailable, note it rather than omitting it silently
- If reported financials are restated or under review, flag this prominently
- If sources conflict (e.g., two data providers show different revenue figures), note the discrepancy and use the attributed source
- If the company does not report a standard metric (e.g., no dividend, no EBITDA disclosure), note this rather than leaving the field blank
- Do not interpolate or estimate unreported figures and present them as reported data

---

## Prohibited Analytical Shortcuts

- Do not lead with a buy/sell/hold recommendation
- Do not present a stock as "safe" or "low risk" without qualification
- Do not state a price target as though Claude calculated it
- Do not summarize a complex earnings report in a single sentiment word ("strong", "weak") without supporting evidence
- Do not omit negative data points because they complicate the narrative
