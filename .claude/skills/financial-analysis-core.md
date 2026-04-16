# Financial Analysis Core — Skill Reference

## Purpose
This skill governs how Aureus reasons about stocks and financial data. It applies to all commands that involve stock analysis, regardless of whether the context is equity research or wealth management.

## Core Reasoning Principles

- **Facts before interpretation.** State what the data shows before drawing conclusions. Label the distinction clearly.
- **No fabricated data.** If a data field is empty or unavailable, say so. Do not invent estimates.
- **Mock data labelling.** All outputs from Phase 1 mock data must carry the note: *[MOCK / NOT REAL-TIME — for framework and internal use only]*.
- **Valuation is context-dependent.** A PE of 28x means something different for a high-growth tech company than for a bank. Always contextualise multiples against sector and growth profile.
- **Thesis integrity.** Every stock view must have a bull case and bear case. Conviction without a bear case is incomplete.

## Output Rules
- Max 3 bullets per section
- No tables in Telegram output
- Separate facts from RM framing
- Disclaimer on every output: *For internal RM use only. Not investment advice.*

## Future Connector Insertion Point
When live market and news connectors are available (Phase 2+), they plug in at `FinancialAnalysisService` in `services/financial_analysis_service.py`. Pass a live `connector` instance — callers do not change.
