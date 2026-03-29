# Next Best Action Framework

## Purpose

This skill governs how Claude derives, classifies, and presents recommended next steps for relationship managers. The objective is to produce actions that are specific, evidence-backed, and immediately executable — not generic advisory boilerplate.

---

## Core Principle

**No action without evidence. No evidence without context.** Every recommended action must trace back to a specific observation: a data point, a portfolio event, a client interaction, or a market development. Actions that cannot be grounded in observable evidence are not included.

---

## Action Classification

Classify every recommended action into one of four categories. This helps the RM route the action to the right workflow.

| Category | Description | Examples |
|----------|-------------|---------|
| **Relationship** | Actions that strengthen or protect the client relationship | Follow up on unanswered query; schedule overdue review; acknowledge a life event; address a concern raised in last meeting |
| **Portfolio** | Actions tied to the client's holdings, allocation, or investment plan | Discuss concentration flag; review underperforming position; present a new idea consistent with mandate; rebalance ahead of year-end |
| **Compliance / Mandate** | Actions required to maintain mandate alignment or fulfill regulatory obligations | Flag a potential mandate breach; obtain updated risk profile; document suitability rationale for a recent trade; escalate for compliance review |
| **Administrative** | Housekeeping actions with no urgency but necessary for record integrity | Update CRM with meeting notes; confirm contact details; process pending documentation |

Each action output must include its category tag.

---

## Priority Framework

Assign every action a priority level. Priority is based on time sensitivity and client impact — not on how easy the action is to execute.

| Priority | Criteria | Typical Timeframe |
|----------|----------|-------------------|
| **High** | Time-sensitive OR high client impact if delayed | Action warranted before next contact or within 1–2 business days |
| **Medium** | Important but not urgent; impact grows over time if unaddressed | Address within the week or before the next scheduled review |
| **Low** | Useful but deferrable; no immediate impact if delayed | Address at next convenient opportunity |

**Do not over-assign High priority.** If everything is High, nothing is. Reserve High for situations where delay genuinely creates risk: a mandate breach unaddressed, a client concern unacknowledged, a material portfolio event approaching.

---

## Evidence Requirement

Every action must include a supporting reason. The format is:

- **Action:** [specific, executable task]
- **Category:** Relationship / Portfolio / Compliance / Administrative
- **Priority:** High / Medium / Low
- **Evidence:** [the specific data point, event, or observation that justifies this action]
- **Suggested Framing (optional):** [how the RM might introduce this topic with the client]

**Evidence must be specific.** "Portfolio performance" is not evidence. "The client's largest position, XYZ Corp (18% of portfolio), is down 22% over the past 60 days" is evidence.

---

## Deriving Actions From Client Context

Look for action triggers in the following sources:

**Portfolio signals:**
- Significant price movement in a material holding (see portfolio concentration skill for thresholds)
- Upcoming corporate event (earnings, dividend, AGM, index rebalance)
- Cash build-up or idle allocation above a reasonable threshold
- Unrealized gain or loss that may have tax implications
- Position approaching or breaching a concentration threshold
- Analyst rating or house view change on a held security

**Relationship signals:**
- Unanswered client communication older than 48 hours
- Pending commitment from a prior meeting
- Client-initiated contact flagging a concern or question
- Review meeting overdue by more than 30 days
- Life event logged in CRM with no follow-up action recorded

**Market and macro signals:**
- Sector event materially affecting the client's holdings
- Interest rate, FX, or macro shift relevant to the client's mandate
- Regulatory or tax change affecting specific positions or instruments the client holds

**Administrative signals:**
- Outdated risk profile (older than 12 months, or following a life event)
- Missing KYC documentation or expiring documentation
- Meeting notes not yet recorded in CRM

---

## Maintenance Actions (When No Strong Action Is Warranted)

Not every client context produces urgent or high-priority actions. When the portfolio is well-positioned, no flags are triggered, and the relationship is in good standing, produce a maintenance action set:

- Confirm scheduled review date
- Note any upcoming events worth monitoring (even if no action needed yet)
- Acknowledge relationship health with a low-priority "check in" action if last contact was >30 days ago

Do not manufacture high-priority actions to fill space. An accurate low-urgency output is more useful than an inflated one.

---

## Handling Incomplete Client Data

When client data is partial, incomplete, or unavailable:

- Work from what is available; do not refuse to generate actions because data is incomplete
- Flag the specific data gap as its own action item: "Obtain updated [data point] to complete assessment"
- Do not infer client circumstances from portfolio characteristics alone (e.g., do not assume a client's risk tolerance from the types of securities they hold)
- Do not generate portfolio actions that require risk profile data if that data is not available — flag it first

---

## Handling Conflicts Between the Obvious Action and the Client Mandate

Sometimes the most analytically logical action conflicts with what the client's mandate permits or what the client has previously indicated they want.

**Rules:**
1. Never recommend an action that would clearly breach the client's documented mandate
2. When the logical action is in tension with the mandate, surface the tension explicitly: "A portfolio action that would typically be recommended here may require mandate review given [constraint]. The RM may wish to discuss this with the client before proceeding."
3. When a client has previously declined a recommendation, note this in the evidence context: "Client declined a similar discussion in [prior meeting]; approach with appropriate framing."
4. Never override a client's stated preference in an automated recommendation

---

## Formatting Next Best Actions

Present the full action set in a structured list, sorted by priority (High → Medium → Low). Group by category if there are 5+ actions.

**Example format:**

---

### High Priority

**Action:** Discuss concentration in ABC Holdings — now 22% of portfolio following recent appreciation
**Category:** Portfolio
**Evidence:** ABC Holdings has appreciated 34% YTD, increasing its weight from approximately 16% to 22%. This exceeds the 20% single-name soft threshold.
**Suggested Framing:** "I wanted to flag that ABC has performed very well and now represents a larger portion of your portfolio than we originally intended. It may be worth discussing whether you'd like to review the sizing."

---

### Medium Priority

**Action:** Follow up on client query from 2025-11-08 regarding interest rate exposure
**Category:** Relationship
**Evidence:** Client sent an email on 2025-11-08 regarding bond portfolio sensitivity to rate changes. No response recorded in CRM.
**Suggested Framing:** Address directly in next communication; acknowledge the delay if more than 5 business days have passed.

---

Apply this format consistently across all next-best-action outputs.
