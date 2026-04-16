# Aureus RM Copilot — Implementation Plan

---

## Phase 1 — MVP (Weeks 1–4)

**Goal:** Working plugin with mock connectors and 3 core commands functional end-to-end.

### Deliverables

- [ ] `.claude/` structure validated (commands, skills, agents, rules, hooks all present)
- [ ] `.mcp.json` with all placeholder servers declared
- [ ] Mock MCP server implemented in Python for: `crm`, `portfolio`, `suitability`
- [ ] Commands working with mock data: `/client-review`, `/stock-brief`, `/meeting-pack`
- [ ] All 7 skill files loaded and active
- [ ] `pre_response_guardrail.py` hook active and catching prohibited patterns
- [ ] JSON schemas validated against sample mock outputs
- [ ] `README.md` and `docs/architecture.md` complete

### Mock Connector Implementation

Build a single `mock_server.py` that implements all placeholder tools returning hardcoded JSON fixtures. Fixtures should cover at least 2 client personas and 3–4 tickers.

**Suggested mock personas:**
- James Tan — balanced, SGD 3M AUM, concentrated Singapore financials
- Sarah Lim — conservative, SGD 8M AUM, diversified multi-asset

**Suggested mock tickers:** D05.SI (DBS), U11.SI (UOB), TSM (TSMC), AAPL (Apple)

### Dependencies

- Claude Code CLI installed and authenticated
- Python 3.10+ for hooks and mock server
- No external APIs required in Phase 1

### Assumptions

- Mock data will be manually maintained for Phase 1
- Compliance team not involved until Phase 2
- Single RM user only; no multi-tenancy in Phase 1
- Output quality review done manually by RM stakeholder

---

## Phase 2 — Core Feature Expansion (Weeks 5–10)

**Goal:** All 8 commands functional, real CRM and portfolio connectors integrated, suitability validation live.

### Deliverables

- [ ] All 8 commands tested end-to-end: add `/portfolio-fit`, `/compare-stocks`, `/next-best-action`, `/risk-check`, `/earnings-update`
- [ ] Real CRM connector live (`crm.get_client_profile`, `crm.get_recent_interactions`)
- [ ] Real portfolio/holdings connector live (`portfolio.get_holdings`, `portfolio.get_exposure_breakdown`)
- [ ] Suitability risk profile connector live (`suitability.get_risk_profile`)
- [ ] Market data connector live (select provider: Bloomberg, Refinitiv, or equivalent)
- [ ] Fundamentals connector live (`fundamentals.get_financials`, `fundamentals.get_estimates`)
- [ ] `source_validation.py` hook active
- [ ] `crm_logger.py` writing to local JSONL log file
- [ ] Schema validation integrated into output pipeline
- [ ] 5 end-to-end test scenarios passing (see Test Plan)

### Connector Integration Priority Order

| Priority | Connector | Reason |
|----------|-----------|--------|
| P1 | CRM — Client Profile | Required for all client-specific commands |
| P1 | Portfolio — Holdings | Required for portfolio-fit, meeting-pack, client-review |
| P1 | Suitability — Risk Profile | Required for suitability guardrails |
| P2 | Market — Company Snapshot | Required for stock-brief, compare-stocks |
| P2 | Fundamentals — Financials | Required for stock-brief, earnings-update |
| P2 | Research — Earnings Summary | Required for earnings-update |
| P3 | House View — Internal View | Enhances stock-brief and portfolio-fit |
| P3 | Compliance — Disclosures | Required for risk-check compliance flags |
| P3 | Notes — Save Meeting Prep | Required for CRM write-back in meeting-pack |

### Dependencies

- CRM API access and credentials (IT/infrastructure team)
- Portfolio system API documentation
- Market data provider contract and API keys
- Internal suitability system API access
- Authentication mechanism agreed (OAuth2 / API key / MTLS)

### Assumptions

- CRM and portfolio systems expose REST or gRPC APIs compatible with MCP tool schema
- Market data provider supports per-ticker fundamentals and estimates
- Suitability data is structured and queryable by client ID

---

## Phase 3 — Enterprise Hardening (Weeks 11–16)

**Goal:** Compliance hooks live, audit logging to enterprise systems, house view integration, multi-RM support.

### Deliverables

- [ ] `pre_response_guardrail.py` connected to compliance-approved prohibited language ruleset
- [ ] `suitability.validate_recommendation_framing` live and integrated into hook pipeline
- [ ] `crm_logger.py` writing to enterprise CRM/notes system via API
- [ ] `notes.save_meeting_prep` and `notes.save_action_item` tools live
- [ ] House view connector live (`house_view.get_internal_view`)
- [ ] Compliance disclosures connector live (`compliance.check_disclosures`, `compliance.get_approved_products`)
- [ ] Audit log schema agreed with compliance and IT
- [ ] Multi-RM support: output tagged with `rm_user` identity
- [ ] Session context isolation between RMs
- [ ] Performance target: P95 response time < 10s for all commands
- [ ] Compliance sign-off on guardrail language rules
- [ ] Pilot with 3–5 RMs and structured feedback collection

### Security and Audit Requirements

- All MCP tool calls logged with: timestamp, tool_name, input_params (PII-masked), client_id, rm_user
- Output logs must not store full client PII in plaintext
- Log retention policy aligned with internal data governance rules
- PII fields in schemas: mask or exclude from logs (`client_name`, `rm_owner`)
- Access to logs restricted to authorized roles

---

## Dependencies (External)

| Dependency | Owner | Required For |
|------------|-------|-------------|
| CRM API access | IT / CRM team | Phase 2 |
| Portfolio system API | IT / Wealth platform team | Phase 2 |
| Market data provider | Vendor procurement | Phase 2 |
| Suitability system API | Risk/Compliance team | Phase 2 |
| Compliance language rules | Compliance team | Phase 3 |
| Legal sign-off on disclaimer text | Legal team | Phase 2 |
| Internal IT MCP server hosting | IT infrastructure | Phase 2 |
| House view data API | Research/Strategy team | Phase 3 |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| CRM API not queryable by client name | Medium | High | Request client_id lookup endpoint; fall back to name-to-ID mapping |
| Market data provider lacks estimates | Low | Medium | Source estimates from separate provider; mark N/A if unavailable |
| Compliance review delays | High | Medium | Use conservative default ruleset in Phase 2; iterate in Phase 3 |
| LLM output variability causes false guardrail flags | Medium | Low | Tune regex against real output samples; use warning not block by default |
| CRM write-back API unavailable in Phase 2 | Medium | Low | Log to local JSONL in Phase 2; connect in Phase 3 |
| Multi-client name collisions | Medium | High | Always require client_id as primary key; treat client_name as display only |

---

## Test Plan

### Unit Tests (Python, `pytest`)

- `test_pre_response_guardrail.py` — test each prohibited pattern with matching and non-matching strings
- `test_source_validation.py` — test claim detection against mock tool results
- `test_crm_logger.py` — test log record structure, file write, and stub methods

### Schema Validation Tests

- Validate all 5 schemas against sample mock outputs using `jsonschema`
- Test required field enforcement and enum constraint enforcement

### Command Output Quality Review Checklist

- [ ] All required sections present
- [ ] No prohibited language
- [ ] Suitability framing present
- [ ] Disclaimer present (where required)
- [ ] No fabricated data (verify against tool output)
- [ ] Output within target word count

### End-to-End Test Scenarios

1. `/client-review "James Tan"` — verify all sections, concentration observation, follow-up surfacing
2. `/stock-brief D05.SI` — verify facts/interpretation separation, house view labeled correctly
3. `/portfolio-fit "James Tan" D05.SI` — verify concentration flag fires (overweight SGD financials)
4. `/risk-check "Sarah Lim" TSM` — verify mandate check passes, risks surfaced correctly
5. `/meeting-pack "James Tan"` — verify agenda, follow-ups, log written to JSONL
