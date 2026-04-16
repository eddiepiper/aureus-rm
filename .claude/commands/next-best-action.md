# /next-best-action [client_name]

Suggest actionable next best actions for the RM based on client context.

## Purpose

This command generates a prioritized list of 3–5 specific, executable actions an RM should consider for a named client. All actions must be grounded in actual client data — no generic relationship management advice. This is a decision support tool, not a compliance approval or investment mandate.

## Data Retrieval Steps

Execute all of the following tool calls before generating output. Do not skip steps. If any call returns no data, note it — do not infer or fabricate.

1. `crm.get_client_profile(client_name)` — client profile, segment, relationship context
2. `crm.get_recent_interactions(client_name, limit=5)` — last 5 interactions, open follow-ups, stated client concerns
3. `portfolio.get_holdings(client_name)` — current holdings
4. `portfolio.get_exposure_breakdown(client_name)` — sector and geographic exposure
5. `suitability.get_risk_profile(client_name)` — risk rating, mandate, constraints, exclusions
6. `house_view.get_internal_view(sectors)` — for sectors with significant client exposure, check for relevant internal views

If the client name does not match a unique record, ask the user to clarify before proceeding.

## Output Format

Generate 3–5 actions. For each action, use the exact structure below. Number actions sequentially.

---

## Action [N]: [Action Title]

- **What:** The specific action the RM should take. Be concrete and executable — not "review the portfolio" but "schedule a portfolio rebalancing conversation focused on the client's overweight position in [sector]."
- **Why:** The rationale tied directly to this client's context, portfolio state, or interaction history. Reference specific data points (e.g., "client is 28% allocated to energy vs. a typical 10–15% band for their risk profile").
- **Supporting Evidence:** The specific data point or observation from the retrieved data that supports this action. Quote or reference the source (CRM note, holding, exposure figure).
- **Suitability Note:** Compliance-appropriate framing for the action. Note any mandate constraints that are relevant. If the action requires a suitability check or product approval before proceeding, state that explicitly.
- **Priority:** High / Medium / Low
- **Suggested Timing:** When should the RM take this action? (e.g., "Before next scheduled meeting," "Within 2 weeks," "At next quarterly review," "Immediately — pending follow-up overdue")

---

Repeat the above block for each of the 3–5 actions.

## Prioritization Logic

When determining priority, weight the following factors:
- **High:** Overdue follow-ups, mandate constraint breaches or near-breaches, time-sensitive market events affecting holdings, compliance flags requiring action
- **Medium:** Portfolio rebalancing opportunities, engagement deepening based on stated client interests, relevant house view updates
- **Low:** Proactive relationship touchpoints, market context sharing, longer-horizon planning conversations

Do not assign all actions the same priority level. If all actions are genuinely equal priority, explain why.

## Behavioral Rules

- Every action must be tied to specific client context — no generic RM advice.
- Do not frame actions as guaranteed to produce outcomes. Use language such as "consider discussing," "may be worth reviewing," "flagged for follow-up," or "worth exploring given."
- Prioritize actions that are actually executable by an RM — not actions that require system changes, product approvals, or compliance sign-off before the RM can even begin.
- If an action requires compliance or product approval before proceeding, flag this explicitly in the Suitability Note.
- If there are open follow-ups from prior interactions that have not been resolved, always surface at least one action to address them.
- Do not fabricate supporting evidence. If the data does not support a specific action, do not generate that action.
