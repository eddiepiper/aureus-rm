# /client-review [client_name]

Generate a relationship manager review summary for a named client.

## Purpose

This command produces a structured client review for RM use before or after a client interaction. It pulls from CRM, portfolio, and suitability systems to give the RM a complete, compliance-aware picture of where the client stands.

## Data Retrieval Steps

Execute the following tool calls in order. If any call fails or returns no data, note "Data not available from CRM." in the relevant section — do not fabricate or infer missing data.

1. `crm.get_client_profile(client_name)` — retrieve full client profile including segment, AUM band, RM owner, and relationship history
2. `crm.get_recent_interactions(client_name, limit=5)` — retrieve the last 5 logged interactions
3. `portfolio.get_holdings(client_name)` — retrieve current portfolio holdings
4. `portfolio.get_exposure_breakdown(client_name)` — retrieve sector and geographic exposure breakdown
5. `suitability.get_risk_profile(client_name)` — retrieve risk rating, investment mandate, and any active constraints or exclusions

If the client name does not match a unique record, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. Use the section headers exactly as shown below.

---

## Executive Summary

2–3 sentences. Cover: who the client is, their segment and AUM band, and the most important contextual note for the RM going into a meeting or review. If there are pending follow-ups or unresolved actions from prior interactions, flag them here.

---

## Portfolio Overview

Present a holdings table with the following columns:

| Ticker | Name | Sector | Weight % | P&L % |
|--------|------|--------|----------|-------|

If holdings data is unavailable, state so explicitly. Do not estimate weights or returns.

---

## Concentration Observations

Bullet points covering:
- Where the client is overweight relative to a reasonable diversified baseline (flag if any single position exceeds 10% or any sector exceeds 30%)
- Where the client is underweight or has notable gaps
- Any geographic concentration risks
- Any single-stock risk or illiquidity concerns

Keep language suitability-appropriate. Do not use alarmist phrasing.

---

## Recent Interactions

Summarize the last 3 logged interactions in brief (1–2 sentences each). Include date, interaction type (call, meeting, email), and key topic or outcome.

If fewer than 3 interactions are on record, note that.

---

## Key Talking Points

3–5 bullet points the RM should have ready for the next client conversation. These should be grounded in the portfolio data, recent interactions, and any open follow-ups — not generic relationship advice.

---

## Suggested Next Actions

Actionable items for the RM, each with:
- The specific action
- Rationale tied to client context or portfolio state
- Whether it requires compliance or product approval before proceeding

Do not frame these as guaranteed to produce outcomes. Use language such as "consider discussing," "may be worth reviewing," or "flagged for follow-up."

---

## Compliance Notes

- List any active mandate constraints or exclusion criteria
- Flag any suitability concerns given current holdings
- Note any required disclosures for planned discussion topics
- If no compliance flags exist, state: "No active compliance flags identified."

---

## Behavioral Rules

- Do not fabricate client data. If data is unavailable from a tool call, state "Data not available from CRM." in that section.
- Do not frame suggested actions as guaranteed outcomes.
- All portfolio commentary must use suitability-appropriate language.
- If pending follow-ups exist in the CRM interaction log, surface them in the Executive Summary and Suggested Next Actions.
- Never omit the Compliance Notes section, even if empty.
