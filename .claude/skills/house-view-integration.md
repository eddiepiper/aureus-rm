# Internal House View Integration

## Purpose

This skill governs how Claude sources, presents, and contextualizes internal house view data within Aureus outputs. The house view is a valuable signal — but it is one input among several, not an objective market verdict. Claude must handle it with appropriate labeling, calibration, and transparency.

---

## Core Principle

**The house view is context for RM discussion, not a client investment directive.** It represents the internal research or investment team's current stance. It must be labeled as such, presented alongside other relevant views where they exist, and never misrepresented as consensus, fact, or recommendation.

---

## Sourcing Internal House View

When house view data is available via `house_view.get_internal_view`:

- Retrieve the view before generating any analysis that touches on a covered security or sector
- Record the following fields: **rating**, **target band** (if available), **key thesis**, **key risks**, **last updated date**
- If the tool returns no result or an error, proceed without the house view and note its absence explicitly

If house view data is not retrieved (tool unavailable, no coverage, or data error), do not substitute an estimated or inferred view. State: "Internal house view not available for this security."

---

## Labeling Requirements

Every use of internal house view data must be clearly and consistently labeled.

**Required label format:**

> **Internal House View — [YYYY-MM-DD]:** [rating / stance] — [brief thesis summary]

**Example:**

> **Internal House View — 2025-10-03:** Overweight — The thesis is based on expected margin expansion in H2 driven by pricing power and moderating input costs. Key risk: demand softness in the European segment.

**Rules:**
- Never present house view content without the date label
- Never blend house view content with analyst consensus without distinguishing them
- Never present the house view as Claude's own interpretation or as an objective market fact
- If the house view has a target band, present it as a range, not a point estimate, and label it as internal

---

## Presenting Conflicting Views

When the internal house view and external analyst consensus diverge, surface both without resolving the conflict. Divergence is informative — it is not an error to be corrected.

**How to present conflicting views:**

1. State each view with its source label and date
2. Briefly characterize the nature of the divergence (directional, magnitude, timing, or thesis-driven)
3. Do not editorialize about which view is correct
4. Flag the divergence as a potential discussion point for the RM

**Example — Internal bearish, consensus bullish:**

> **Internal House View — 2025-09-15:** Underweight — Concerns around deteriorating free cash flow and aggressive capex guidance that may pressure returns over the next 12 months.
>
> **Analyst Consensus:** 14 of 20 analysts rate Buy, with a median 12-month price target of USD 88.
>
> **Note:** The internal view is more cautious than consensus. The divergence centers on capex assumptions and the timeline for FCF recovery. RMs may wish to discuss this with clients who hold the name.

**Example — Internal neutral, consensus bullish:**

> **Internal House View — 2025-10-20:** Neutral — No strong directional view at current valuation. The investment thesis is intact but the near-term risk/reward is considered balanced.
>
> **Analyst Consensus:** 11 of 16 analysts rate Buy. Median target implies ~18% upside.
>
> **Note:** The internal team does not currently share consensus enthusiasm. RMs should be aware of this divergence when presenting the name to clients.

---

## Handling Stale House View Data

A house view is considered potentially stale if it was last updated more than **60 days** ago.

**When house view is more than 60 days old:**
- Display the data with a staleness flag: "**[Note: Last updated [date] — may not reflect recent developments]**"
- Do not suppress the stale view — it may still be directionally useful
- Flag it as a potential action item: "Confirm whether an updated house view is available before presenting this to the client"
- If a significant event has occurred since the last update (earnings, M&A announcement, macro shift), note the event explicitly and flag that the house view predates it

**Staleness thresholds:**

| Days Since Update | Treatment |
|------------------|-----------|
| 0–30 days | Current; present normally |
| 31–60 days | Present normally; no flag required |
| 61–90 days | Flag as potentially stale |
| >90 days | Flag prominently; recommend verification before client use |

---

## Presenting a Neutral House View

A neutral stance is a substantive position — it means the internal team sees the risk/reward as balanced and does not have a strong directional view. Present it clearly.

**Do not:**
- Imply that neutral means "no view" or "uninformed"
- Interpret neutral as a soft positive or soft negative
- Present neutral as equivalent to a hold recommendation

**Do:**
- State the neutral stance clearly with the required label
- Summarize the rationale for the neutral view (e.g., valuation in-line, thesis intact but upside limited, waiting for a catalyst)
- Note whether the neutral view represents a downgrade from a prior positive view or an upgrade from a prior negative view, if that context is available

**Example:**

> **Internal House View — 2025-11-01:** Neutral — Current valuation is considered fair relative to the sector. The growth outlook is positive but largely priced in at current levels. The team is monitoring for margin improvement signals before considering a constructive upgrade.

---

## What a House View Typically Contains

For reference, when processing or presenting house view data, expect the following fields:

| Field | Description |
|-------|-------------|
| **Rating** | Overweight / Underweight / Neutral (or equivalent internal nomenclature) |
| **Target Band** | Price range representing internal fair value estimate (if provided) |
| **Key Thesis** | 1–2 sentence rationale for the current stance |
| **Key Risks** | Primary risks that could invalidate the thesis |
| **Last Updated** | Date of most recent review |
| **Coverage Status** | Whether the security is actively covered by the internal team |

If any of these fields are missing from the retrieved data, note the gap rather than leaving it blank silently.

---

## House View in Client-Facing Context

When house view content appears in outputs that will be shared with or presented to clients:

- The label must still be present ("Internal House View — [date]")
- The RM must review the content before distribution
- The house view should be framed as "our current view" rather than "the market's view"
- Do not present the house view as a recommendation or instruction to act
- Apply the standard disclaimer (see suitability-response-style skill) to any client-facing output containing house view content

---

## House View Is Not a Substitute for Suitability Assessment

A positive internal house view does not mean a security is suitable for a given client. Suitability depends on:
- The client's risk profile and mandate
- The client's existing portfolio concentration
- The client's stated objectives and constraints
- The client's investment horizon

Never use house view alignment as a proxy for suitability. They are separate considerations and must be treated as such.
