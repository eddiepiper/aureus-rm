# /meeting-pack [client_name]

Prepare a full RM meeting pack for a specific client.

## Purpose

This command produces a complete, printable or digitally shareable meeting pack for an RM ahead of a scheduled client meeting. It is RM-facing — not client-facing. The goal is to give the RM everything they need to run a productive, well-prepared meeting in a format that is scannable in under 3 minutes.

## Data Retrieval Steps

Execute all of the following tool calls before generating output. Do not skip steps. If any call returns no data, note the gap — do not fabricate.

1. `crm.get_client_profile(client_name)` — full client profile
2. `crm.get_recent_interactions(client_name, limit=5)` — last 5 interactions, including any open follow-ups
3. `portfolio.get_holdings(client_name)` — current holdings
4. `portfolio.get_exposure_breakdown(client_name)` — sector and geographic breakdown
5. `suitability.get_risk_profile(client_name)` — risk rating, mandate, constraints
6. `house_view.get_internal_view(sectors)` — for any sectors with significant client exposure, retrieve relevant internal views
7. `research.search_news(tickers, days=30)` — for any holdings with notable recent news, retrieve updates

After generating the output, call:
8. `notes.save_meeting_prep(client_name, output)` — log the meeting pack output to the CRM notes system

If the client name does not match a unique record, ask the user to clarify before proceeding.

## Output Format

Respond in strict markdown. This document is designed to be printed or shared digitally. Use the section headers exactly as shown below. Prioritize relevance over completeness — surface what matters, not everything available.

---

## Meeting Pack: [Client Name] — [Date]

*Prepared by Aureus RM Copilot | For internal RM use only | Not for client distribution*

---

## Client Summary

- **Segment:** [e.g., Private Banking / Ultra-HNW / Institutional]
- **AUM band:** [value or "not disclosed"]
- **RM owner:** [name from CRM]
- **Relationship tenure:** [years on record]
- **Relationship summary:** 2–3 sentences summarizing the nature of the relationship, key client priorities, and any defining context the RM should hold top of mind going into this meeting.

---

## Portfolio Summary

- Total AUM band: [value]
- Number of holdings: [count]
- Key concentration points: [top 3 positions by weight]
- Asset class mix: [equity / fixed income / alternatives / cash breakdown if available]
- Risk rating: [value from suitability profile]

If full holdings data is unavailable, note that and provide whatever partial data is available.

---

## Portfolio Developments Since Last Meeting

Bullet points covering notable changes since the last logged interaction:
- Significant price moves in existing holdings (flag anything >±10% where identifiable)
- Any corporate events (earnings, dividends, M&A, management changes) affecting holdings
- Macro or sector-level developments relevant to the client's exposure

If no material developments are identified, state that. Do not pad this section.

---

## Discussion Topics

3–5 items with brief context for each. These should be grounded in the portfolio state, recent interactions, and any open follow-ups — not generic relationship topics.

For each topic:
- **Topic:** [title]
- **Context:** [1–2 sentences on why this is relevant now]
- **Compliance note:** [flag if any required disclosure or approval applies, otherwise omit]

---

## Relevant Market Context

2–4 bullet points on macro or sector themes directly relevant to this client's portfolio and mandate. Keep this tight — only include what the RM actually needs for this specific client. Avoid generic market commentary.

---

## Suggested Agenda

A time-boxed agenda for the meeting. Adjust timing based on the number and complexity of discussion topics. Example structure:

| Time | Item |
|------|------|
| 0–5 min | Relationship check-in |
| 5–15 min | Portfolio review |
| 15–30 min | Discussion topic 1 |
| 30–40 min | Discussion topic 2 |
| 40–50 min | Open follow-ups |
| 50–60 min | Wrap-up and next steps |

Adjust or compress as appropriate. Flag if any agenda item requires pre-meeting compliance clearance.

---

## Open Follow-ups

List any unresolved actions from prior interactions (sourced from CRM interaction log). For each:
- **Follow-up:** [description]
- **Opened:** [date]
- **Status:** [pending / in progress / requires RM action before meeting]

If no open follow-ups: state "No open follow-ups on record."

Flag open follow-ups that should be resolved before the meeting.

---

## Preparation Checklist

Actionable items the RM should verify or complete before the meeting:

- [ ] Confirm meeting logistics (time, format, attendees)
- [ ] Review open follow-ups and prepare updates
- [ ] Verify any required compliance disclosures for planned discussion topics
- [ ] Confirm internal house view is current for relevant holdings or sectors
- [ ] Check for any new news or developments on key holdings since this pack was generated
- [Add any client-specific items surfaced from the data above]

---

## Behavioral Rules

- This pack is RM-facing, not client-facing. Do not use language intended for the client to read directly.
- Flag compliance and follow-up items prominently — do not bury them.
- Do not overload with data. Include only what is relevant to this meeting and this client.
- Structure must be scannable in under 3 minutes — use bullets, tables, and short paragraphs.
- Do not fabricate data. If any data source is unavailable, note it explicitly.
- After generating the output, always call `notes.save_meeting_prep` to log the pack.
