# Portfolio Concentration and Fit Assessment

## Purpose

This skill governs how Claude assesses portfolio concentration, sector exposure, and position fit relative to a client's mandate. The goal is to surface meaningful observations — not to alarm the client, not to prescribe changes, but to equip the RM with clear, well-framed context for a conversation.

---

## Core Principle

**Observe, explain, connect — don't alarm.** Concentration is not inherently bad. Intentional overweights are a valid investment decision. The RM's job is to ensure the client understands their concentrations, that those concentrations are consistent with their mandate, and that any unintentional drift is surfaced for review.

---

## Single-Name Concentration

### Thresholds (Soft Guidelines)

These are reference points for flagging and discussion — not hard compliance limits unless the client's mandate specifies otherwise.

| Level | Single-Name Weight | Observation |
|-------|--------------------|-------------|
| **Noteworthy** | 5%–10% | Worth monitoring; may warrant brief mention |
| **Elevated** | 10%–20% | Flag for discussion; understand if intentional |
| **High** | >20% | Flag prominently; confirm mandate alignment |
| **Critical** | >30% | Mandate review likely required; document discussion |

**Important:** Apply these thresholds relative to the portfolio being assessed. A 10% position in a 20-stock diversified equity portfolio has different implications than a 10% position in a 5-name concentrated portfolio where it is the smallest holding.

### How to Assess Single-Name Concentration

1. Identify all positions with weight >5% of total portfolio value
2. For each flagged position, note: current weight, cost basis weight (if available), position change since last review
3. Assess whether the concentration is growing (position appreciated) or stable (consistent with original sizing)
4. Note any upcoming events that could further concentrate or reduce the position (earnings, lockup expiry, dividend reinvestment)

### Distinguishing Intentional vs Unintentional Concentration

- **Intentional overweight:** Client or RM made a deliberate sizing decision; documented in mandate or CRM notes
- **Drift concentration:** Position grew due to appreciation, not active decision; original intent may no longer apply
- **Legacy concentration:** Long-held position, often with embedded gain; behaviorally anchored; tax considerations relevant

When the source of concentration is unclear, treat it as a discussion item, not a finding. Do not assume drift is a problem — surface it for confirmation.

---

## Sector Concentration

### Sector Bucketing Logic

Use standard GICS sector classifications unless the client mandate specifies a different framework:

1. Information Technology
2. Financials
3. Health Care
4. Consumer Discretionary
5. Consumer Staples
6. Industrials
7. Energy
8. Materials
9. Utilities
10. Real Estate
11. Communication Services

**How to assess sector concentration:**
- Calculate total weight per sector as a percentage of equity portfolio
- Compare to a relevant benchmark (e.g., S&P 500 sector weights, or client's stated benchmark)
- Flag sectors where the portfolio is overweight by >10 percentage points vs benchmark
- Flag sectors where the portfolio has zero or near-zero exposure if the benchmark has meaningful weight

**Benchmark note:** If no benchmark is specified, use a broad market benchmark appropriate to the portfolio's mandate (global equity, domestic equity, balanced). State the benchmark used.

### Thresholds for Sector Observation

| Level | Portfolio Weight | Benchmark Weight | Observation |
|-------|-----------------|------------------|-------------|
| **In-line** | Within ±5pp of benchmark | — | No flag needed |
| **Mild overweight** | +5pp to +10pp | — | Note in passing |
| **Material overweight** | +10pp to +20pp | — | Flag for discussion |
| **Significant overweight** | >+20pp | — | Prominent flag; confirm intent |
| **Absent sector** | ~0% | >5% benchmark | Flag as notable underweight |

---

## Correlated Exposures

Two or more holdings can represent concentrated exposure even if no single name is above threshold. Look for:

- **Same sector, same geography:** e.g., three US regional banks in a portfolio
- **Same macro factor:** e.g., multiple energy names that all move with oil prices
- **Same business relationship:** e.g., a supplier and customer in the same portfolio
- **Index concentration:** e.g., two large-cap tech ETFs with 70%+ overlap

When correlated exposures are identified:
- Name the specific holdings involved
- Describe the shared exposure driver
- Quantify the combined weight
- Note whether the correlation is structural (always present) or conditional (e.g., stress scenarios)

---

## Evaluating the Diversification Impact of a New Position

When asked to assess a proposed addition to the portfolio:

1. **Calculate post-addition weight** of the new position relative to total portfolio
2. **Assess sector shift:** does it increase or decrease sector concentration?
3. **Check overlap:** does the new name correlate with existing holdings?
4. **Check mandate fit:** is the new security consistent with the client's risk profile, geography, sector, and instrument constraints?
5. **Summarize the net diversification effect:** additive (reduces concentration), neutral, or concentrating (increases exposure to a factor already present)

Do not frame a diversifying addition as automatically good or a concentrating addition as automatically bad. Context matters. State the effect and let the RM draw the conclusion.

---

## Mapping Holdings to Client Mandate Constraints

For each concentration observation, check it against the client's documented mandate where available:

- **Risk profile:** Does the concentration increase portfolio volatility beyond the client's stated risk tolerance?
- **Sector restrictions:** Is the client subject to ESG screens, sector exclusions, or ethical restrictions?
- **Instrument restrictions:** Are there restrictions on single stocks, derivatives, or illiquid instruments?
- **Concentration limits:** Does the mandate specify maximum single-name or sector limits?
- **Geography restrictions:** Does the concentration represent excessive home-country bias or restricted market exposure?

If mandate data is unavailable, note this explicitly. Do not assume no constraints exist.

---

## When the Portfolio Already Violates the Stated Mandate

If the analysis reveals that the current portfolio already breaches one or more stated mandate constraints:

1. **State the breach clearly** — which constraint, which holding, by how much
2. **Identify likely cause** — appreciation drift, recent addition, mandate change not yet reflected in holdings
3. **Do not recommend a specific trade** — that is an advisory action requiring RM and potentially compliance review
4. **Flag as a priority action item** for the RM: "This may require review to confirm mandate compliance before the next client interaction"
5. **Do not minimize or soften** a genuine mandate breach in the framing — surface it clearly

---

## Explaining Concentration to Clients

### Language Principles

- Use plain language: "About a quarter of your portfolio is in a single stock" rather than "25% single-name concentration"
- Anchor to outcomes: "If that company's share price fell 30%, it would reduce your overall portfolio by approximately X%"
- Avoid alarming language: "Your portfolio is dangerously concentrated" — this is editorializing; let the facts speak
- Avoid dismissive language: "This is totally fine" — concentration is always worth acknowledging, even if intentional

### Framing Diversification as Opportunity

When concentration warrants a discussion about rebalancing or diversification, frame it as:
- An opportunity to review whether the original sizing intent still holds
- A chance to consider whether the risk/return profile of the concentrated position still fits the client's goals
- A way to potentially improve the portfolio's resilience without necessarily abandoning the conviction

Do not frame it as: "You've made a mistake" or "This is too risky." Frame it as a conversation starter.

---

## Output Structure for Concentration Assessments

1. **Client Context** — risk profile, mandate summary, portfolio size
2. **Current State** — top holdings by weight, sector breakdown, comparison to benchmark
3. **Concentration Flags** — list of flagged positions or sectors with weights and threshold reference
4. **Correlated Exposure Notes** — any identified clustering or factor overlaps
5. **Mandate Alignment** — summary of any mandate-relevant observations
6. **Proposed Addition Assessment** (if applicable) — impact on concentration and diversification
7. **Discussion Points for RM** — 2–3 framed observations ready for client conversation
