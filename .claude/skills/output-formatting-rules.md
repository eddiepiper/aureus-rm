# Output Formatting Rules

## Purpose

This skill defines the standard structure, formatting conventions, and length guidelines for all Aureus RM Copilot outputs. These rules apply to all commands unless a specific command's skill overrides them. Consistency in formatting is not cosmetic — it directly affects how quickly an RM can scan and use the output.

---

## Section Structure

All outputs use the following heading and formatting hierarchy:

- **H2 (`##`)** for main sections
- **H3 (`###`)** for sub-sections where needed
- **H4 (`####`)** only in complex nested outputs (use sparingly)
- **Tables** for comparative data (financials, holdings, multi-attribute comparisons)
- **Bullet lists** for observations, risks, actions, and feature lists
- **Bold** for labels, key terms, field names, and action headings
- **Horizontal rules (`---`)** to separate major sections in outputs longer than 400 words

Do not use italics for emphasis in RM-facing outputs. Reserve italics for attributions, titles, and technical terms if needed.

---

## Section Order by Command Type

Every command type follows a fixed section order. Do not reorder sections arbitrarily.

### `/stock-brief`
1. Overview
2. Performance
3. Financials
4. Catalysts
5. Risks
6. Framing (RM discussion context)
7. Disclaimer (if applicable)

### `/client-review`
1. Client Summary
2. Portfolio Overview
3. Observations
4. Actions
5. Disclaimer

### `/meeting-pack`
1. Client Summary
2. Portfolio Snapshot
3. Talking Points
4. Suggested Agenda
5. Follow-Up Actions
6. Disclaimer (if client-facing)

### `/portfolio-fit`
1. Client Context
2. Current Portfolio State
3. Impact of Proposed Change
4. Assessment
5. Risks
6. Disclaimer

### `/risk-check`
1. Portfolio Summary
2. Risk Flags
3. Mandate Alignment
4. Recommended Actions
5. Disclaimer (if applicable)

### `/earnings-update`
1. Company and Quarter Overview
2. Key Results vs Expectations
3. Management Guidance Summary
4. What Changed vs Prior Quarter
5. Implications for Holders
6. Disclaimer (if applicable)

### `/compare-stocks`
1. Overview of Both Securities
2. Comparative Financials (table)
3. Relative Valuation
4. Differentiating Factors
5. House View and Consensus Summary
6. Framing for Client Discussion
7. Disclaimer

### `/next-best-action`
1. Client Context (1–3 lines)
2. Actions — sorted High → Medium → Low
3. Disclaimer (if applicable)

---

## Data Presentation Rules

### Tables
- All tables must include column headers
- Include units in the header row (e.g., "Revenue (USD M)", "Margin (%)", "P/E (x)")
- Use consistent decimal places within a column (e.g., all margins to one decimal place)
- Align numeric columns right; align text columns left
- For comparison tables, include a "vs Prior Period" or "vs Benchmark" column where relevant

### Percentages
- Always include the `%` symbol (do not write "20 percent" or bare "20")
- Use one decimal place for precision (e.g., 14.3%, not 14% or 14.27%)
- Exception: round numbers (e.g., exactly 10%) may omit the decimal

### Monetary Values
- Always include the currency code before the amount: USD 1.2B, GBP 450M, EUR 3.7B
- Use standard abbreviations: K (thousands), M (millions), B (billions)
- Do not mix abbreviations within the same table (do not use "USD 1.2B" and "USD 850M" in the same column — choose one magnitude)

### Dates
- **In data and tables:** ISO format — YYYY-MM-DD (e.g., 2025-11-15)
- **In documents and narrative text:** Readable format — 15 November 2025 or November 15, 2025
- **In section headers and labels:** Use the fiscal quarter label where applicable (Q3 2025, FY 2024)

### N/A vs Not Available
- **N/A:** The field exists for this data type but the value is zero, nil, or not applicable (e.g., a company with no dividend: Dividend Yield — N/A)
- **Not available:** The data point exists in principle but could not be retrieved at the time of generation (e.g., house view could not be fetched: Internal House View — Not available)
- Do not leave fields blank without one of these two labels

---

## Length Guidelines

These are targets, not hard limits. Use judgment — a complex situation may warrant more length; a simple data update may need less.

| Command | Target Length |
|---------|--------------|
| `/stock-brief` | 400–600 words |
| `/client-review` | 500–700 words |
| `/meeting-pack` | 600–900 words |
| `/portfolio-fit` | 400–600 words |
| `/risk-check` | 300–400 words |
| `/earnings-update` | 400–500 words |
| `/compare-stocks` | 500–700 words |
| `/next-best-action` | 300–500 words (across all actions) |

**Length discipline principles:**
- Do not pad outputs to reach the minimum. A well-structured 350-word output is better than a padded 500-word one.
- Do not truncate to meet the maximum if material information would be cut. Flag that extended analysis is available if needed.
- Tables do not count toward word count targets.

---

## Mandatory Footer for Client-Facing Outputs

All outputs designated for client distribution must end with the following disclaimer section. Do not modify the disclaimer text.

---

**Disclaimer**

This output was generated by the Aureus RM Copilot for internal use by the relationship manager. It does not constitute investment advice and should not be distributed to clients without review and approval by an authorized representative. Past performance does not guarantee future results.

---

For the full extended disclaimer (required when the output discusses specific securities or suitability), refer to the suitability-response-style skill for the complete text.

---

## Formatting Dos and Don'ts

| Do | Do Not |
|----|--------|
| Use headers to make outputs scannable | Use dense paragraphs where bullets would serve better |
| Use tables for multi-attribute data | Use tables for single-column lists |
| Bold key terms and labels | Bold entire sentences or paragraphs |
| Separate major sections with `---` | Use excessive whitespace or blank lines within sections |
| State "Not available" for missing data | Leave fields blank or silently omit them |
| Use ISO dates in data fields | Mix date formats within the same output |
| Use standard currency codes (USD, GBP, EUR) | Use symbols ($ £ €) in formal RM outputs |
| Label all sources (house view, consensus, AI-generated) | Present interpreted content as objective fact |
