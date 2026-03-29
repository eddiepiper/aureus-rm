# Aureus RM Copilot — Example Prompts

Realistic scenarios an RM would encounter. Each shows the command to use, what the system retrieves, and what to expect.

---

## Scenario 1: Client overexposed to Singapore banks asks about adding DBS

**Context:**
James Tan, balanced-risk, SGD 3M AUM. Portfolio: 18% Singapore financials (DBS 9%, UOB 6%, OCBC 3%). Mandate max sector = 20%. Client wants to add more DBS.

**Command:** `/portfolio-fit`

```
/portfolio-fit "James Tan" D05.SI
```

**System retrieves:**
- `crm.get_client_profile` — confirms profile and AUM band
- `suitability.get_risk_profile` — balanced, max sector 20%
- `portfolio.get_holdings` + `portfolio.get_exposure_breakdown` — confirms 18% SGD financials
- `market.get_company_snapshot` + `fundamentals.get_financials` for D05.SI
- `compliance.check_disclosures` for D05.SI
- `house_view.get_internal_view` for D05.SI

**Expected output:**
- Concentration flag: adding DBS pushes SGD financials to ~23% — above mandate
- Fit verdict: **Requires Review**
- Suitability framing: addition would breach sector mandate without a prior trim
- Compliance notes if any disclosures apply

---

## Scenario 2: Compare DBS vs UOB for a balanced client

**Context:**
RM wants talking-points comparison of DBS and UOB. Client is considering rotating between the two.

**Command:** `/compare-stocks`

```
/compare-stocks D05.SI U11.SI
```

**System retrieves:**
- `market.get_company_snapshot` for both
- `fundamentals.get_financials` (TTM) for both
- `fundamentals.get_estimates` for both
- `research.search_news` (30 days) for both
- `house_view.get_internal_view` for both

**Expected output:**
- Side-by-side financials table (revenue, margins, P/E, P/B, ROE, dividend yield)
- Business model comparison: DBS digital-first vs UOB ASEAN SME focus
- Performance comparison (3m, 1y, YTD)
- Key differentiators: ROE, dividend, franchise geography
- Suitability contexts for each name
- No winner declared — supports RM discussion

---

## Scenario 3: Meeting pack for client with concentrated tech holdings

**Context:**
Sarah Lim, growth-oriented, SGD 8M AUM, 35% in US tech (AAPL, MSFT, NVDA, TSM). Quarterly review meeting upcoming. Tech has been volatile.

**Command:** `/meeting-pack`

```
/meeting-pack "Sarah Lim"
```

**System retrieves:**
- `crm.get_client_profile` + `crm.get_recent_interactions` (last 5)
- `portfolio.get_holdings` + `portfolio.get_exposure_breakdown`
- `suitability.get_risk_profile` — growth, max single name 15%
- `research.search_news` for top holdings
- `house_view.get_internal_view` for US tech sector
- Saves to `notes.save_meeting_prep`

**Expected output:**
- Portfolio summary: 35% US tech flagged as concentration observation
- Discussion topics: tech volatility, diversification opportunity, NVDA earnings reaction, currency hedging
- Suggested 60-min agenda
- Open follow-ups from last interaction
- Preparation checklist for RM

---

## Scenario 4: Summarize Q4 2024 earnings for DBS

**Context:**
DBS reported Q4 2024. RM needs a quick summary before client calls.

**Command:** `/earnings-update`

```
/earnings-update D05.SI Q4FY2024
```

**System retrieves:**
- `research.get_earnings_summary` for D05.SI, Q4FY2024
- `fundamentals.get_financials` for reported period
- `fundamentals.get_estimates` — actual vs consensus
- `research.search_news` (post-earnings, 7 days)
- `house_view.get_internal_view` post-earnings

**Expected output:**
- Headline: NII, net profit, fee income — actual vs consensus, beat/miss labeled
- What beat and what missed (line by line)
- Management tone: NIM guidance, dividend commentary
- What changed vs prior narrative (e.g. NIM compression signaled for FY2025)
- Implications for client conversations

---

## Scenario 5: Next best action after portfolio review for conservative client

**Context:**
Margaret Wong, conservative, SGD 5M AUM, not contacted in 3 months. Fixed income drifted to 55%, equities 30%, cash 15%. One SGX-listed bond matures in 60 days.

**Command:** `/next-best-action`

```
/next-best-action "Margaret Wong"
```

**System retrieves:**
- `crm.get_client_profile` + `crm.get_recent_interactions`
- `portfolio.get_holdings` + `portfolio.get_exposure_breakdown`
- `suitability.get_risk_profile`
- `house_view.get_internal_view` for relevant sectors

**Expected action types:**
- **Relationship:** Schedule quarterly review — 3 months no contact
- **Portfolio:** Maturing bond reinvestment discussion — 60 days to maturity, 15% cash available
- **Administrative:** Suitability profile refresh — last review 14 months ago

---

## Scenario 6: Quick stock brief for TSMC before a client call

**Command:** `/stock-brief`

```
/stock-brief TSM
```

**System retrieves:** company snapshot, 3m/1y price history, TTM financials, consensus estimates, 30-day news, house view.

**Expected output:** 400–600 word brief covering TSMC's semiconductor supply chain position, AI demand tailwinds, valuation vs historical range, geopolitical risk, and an RM framing note.

---

## Scenario 7: Risk check before discussing Nvidia with a conservative client

**Context:**
Conservative client Margaret Wong has heard about Nvidia. RM wants to assess whether it is appropriate to discuss.

**Command:** `/risk-check`

```
/risk-check "Margaret Wong" NVDA
```

**System retrieves:**
- `suitability.get_risk_profile` — conservative
- `portfolio.get_holdings` — zero current tech exposure
- `market.get_company_snapshot` + `fundamentals.get_financials` for NVDA
- `compliance.check_disclosures` for NVDA
- `research.search_news` (recent)

**Expected flags:**
- Mandate flag: NVDA volatility profile may not align with conservative mandate
- Concentration flag: adding NVDA introduces concentrated single-name tech to a zero-tech portfolio
- RM approach guidance: present as educational only; if strong client interest, discuss diversified tech ETF as mandate-appropriate alternative
