"""
services/response_formatter.py

Formats structured data into Telegram-readable text.
Keeps messages short, scannable, and mobile-friendly.
Sections are separated with a blank line. Bullets use a dash.
"""

MOCK_BANNER = "⚠️ *MOCK MODE* — Data below is illustrative only.\n\n"


def mock_note(is_mock: bool) -> str:
    return MOCK_BANNER if is_mock else ""


def format_client_review(ctx: dict) -> str:
    c = ctx["customer"]
    holdings = ctx.get("holdings", [])
    interactions = ctx.get("interactions", [])
    tasks = ctx.get("tasks", [])

    lines = [mock_note(ctx.get("is_mock", False))]

    # Header
    lines.append(f"*Client Review — {c.get('preferred_name') or c.get('full_name')}*")
    lines.append("")

    # Profile
    lines.append("*Profile*")
    lines.append(f"- Segment: {c.get('segment', 'N/A')}")
    lines.append(f"- Risk: {c.get('risk_profile', 'N/A')}")
    lines.append(f"- Objective: {c.get('investment_objective', 'N/A')}")
    lines.append(f"- Horizon: {c.get('investment_horizon', 'N/A')}")
    lines.append(f"- Last Review: {c.get('last_review_date', 'N/A')}")
    lines.append(f"- Next Due: {c.get('next_review_due', 'N/A')}")
    lines.append("")

    # Holdings summary
    lines.append("*Portfolio*")
    if holdings:
        for h in holdings[:6]:  # cap at 6 for readability
            pnl = h.get("unrealized_pnl_pct", 0)
            pnl_str = f"+{pnl:.1f}%" if float(pnl) >= 0 else f"{pnl:.1f}%"
            lines.append(
                f"- {h.get('ticker')} {h.get('security_name', '')} "
                f"| {h.get('portfolio_weight_pct', 0):.1f}% | P&L: {pnl_str}"
            )
    else:
        lines.append("- No holdings on file.")
    lines.append("")

    # Concentration note
    sectors: dict = {}
    for h in holdings:
        s = h.get("sector", "Other")
        sectors[s] = sectors.get(s, 0) + float(h.get("portfolio_weight_pct", 0))
    if sectors:
        lines.append("*Concentration*")
        for sector, pct in sorted(sectors.items(), key=lambda x: -x[1]):
            flag = " ⚠️" if pct > 20 else ""
            lines.append(f"- {sector}: {pct:.1f}%{flag}")
        lines.append("")

    # Recent interactions
    lines.append("*Recent Interactions*")
    if interactions:
        for i in interactions[:3]:
            followup = " 🔔 Follow-up pending" if i.get("follow_up_required", "").lower() == "yes" else ""
            lines.append(f"- {i.get('interaction_date')} | {i.get('channel')} — {i.get('summary', '')}{followup}")
    else:
        lines.append("- No recent interactions on file.")
    lines.append("")

    # Open tasks
    lines.append("*Open Actions*")
    if tasks:
        for t in tasks:
            lines.append(f"- [{t.get('urgency', '')}] {t.get('action_title', '')} — due {t.get('due_date', 'TBD')}")
    else:
        lines.append("- No open tasks.")
    lines.append("")

    lines.append("_This output is for internal RM use only. Not for client distribution._")
    return "\n".join(lines)


def format_portfolio_fit(ctx: dict) -> str:
    c = ctx["customer"]
    holdings = ctx.get("holdings", [])
    ticker = ctx.get("ticker", "")

    lines = [mock_note(ctx.get("is_mock", False))]
    lines.append(f"*Portfolio Fit — {c.get('preferred_name') or c.get('full_name')} / {ticker}*")
    lines.append("")

    lines.append("*Client Mandate*")
    lines.append(f"- Risk: {c.get('risk_profile', 'N/A')}")
    lines.append(f"- Objective: {c.get('investment_objective', 'N/A')}")
    lines.append(f"- Restricted markets: {c.get('restricted_markets') or 'None'}")
    lines.append(f"- Product restrictions: {c.get('product_restrictions') or 'None'}")
    lines.append("")

    # Current exposure
    lines.append("*Current Portfolio*")
    total_weight = 0.0
    for h in holdings:
        lines.append(
            f"- {h.get('ticker')} | {h.get('sector')} | {h.get('portfolio_weight_pct', 0):.1f}%"
        )
        total_weight += float(h.get("portfolio_weight_pct", 0))

    lines.append("")

    # Sector breakdown
    sectors: dict = {}
    for h in holdings:
        s = h.get("sector", "Other")
        sectors[s] = sectors.get(s, 0) + float(h.get("portfolio_weight_pct", 0))

    # Check if ticker already held
    existing = next((h for h in holdings if h.get("ticker", "").upper() == ticker), None)
    if existing:
        lines.append(f"ℹ️ {ticker} already held at {existing.get('portfolio_weight_pct', 0):.1f}% of portfolio.")
    else:
        lines.append(f"ℹ️ {ticker} not currently held.")
    lines.append("")

    lines.append("*Concentration Check*")
    for sector, pct in sorted(sectors.items(), key=lambda x: -x[1]):
        flag = " ⚠️ above 20%" if pct > 20 else ""
        lines.append(f"- {sector}: {pct:.1f}%{flag}")
    lines.append("")

    lines.append(
        "⚠️ *Note:* Live stock data not available in MVP. "
        "Full suitability assessment requires market data connector. "
        "Use /stock-brief [ticker] in Claude for detailed stock analysis."
    )
    lines.append("")
    lines.append("_Internal RM use only. Not for client distribution._")
    return "\n".join(lines)


def format_meeting_pack(ctx: dict) -> str:
    c = ctx["customer"]
    holdings = ctx.get("holdings", [])
    interactions = ctx.get("interactions", [])
    watchlist = ctx.get("watchlist", [])
    tasks = ctx.get("tasks", [])

    lines = [mock_note(ctx.get("is_mock", False))]
    lines.append(f"*Meeting Pack — {c.get('preferred_name') or c.get('full_name')}*")
    lines.append("")

    lines.append("*Client Summary*")
    lines.append(f"- {c.get('segment')} | {c.get('risk_profile')} | {c.get('investment_objective')}")
    lines.append(f"- Last review: {c.get('last_review_date', 'N/A')} | Next due: {c.get('next_review_due', 'N/A')}")
    if c.get("notes_summary"):
        lines.append(f"- Notes: {c.get('notes_summary')}")
    lines.append("")

    lines.append("*Top Holdings*")
    for h in holdings[:5]:
        pnl = float(h.get("unrealized_pnl_pct", 0))
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        lines.append(f"- {h.get('ticker')} {h.get('security_name')} | {h.get('portfolio_weight_pct', 0):.1f}% | {pnl_str}")
    lines.append("")

    lines.append("*Recent Interactions*")
    for i in interactions[:3]:
        followup = " 🔔" if i.get("follow_up_required", "").lower() == "yes" else ""
        lines.append(f"- {i.get('interaction_date')} {i.get('channel')}: {i.get('summary', '')}{followup}")
    if not interactions:
        lines.append("- None on file.")
    lines.append("")

    if watchlist:
        lines.append("*Watchlist*")
        for w in watchlist:
            lines.append(f"- {w.get('ticker')} {w.get('security_name')} — {w.get('reason_for_interest', '')}")
        lines.append("")

    lines.append("*Open Actions*")
    for t in tasks:
        lines.append(f"- [{t.get('urgency')}] {t.get('action_title')} — {t.get('due_date', 'TBD')}")
    if not tasks:
        lines.append("- None open.")
    lines.append("")

    lines.append("*Suggested Agenda*")
    lines.append("1. Portfolio performance review")
    lines.append("2. Market update relevant to holdings")
    lines.append("3. Review open actions")
    lines.append("4. Watchlist discussion")
    lines.append("5. Next steps and follow-ups")
    lines.append("")

    lines.append("_Internal RM use only. Not for client distribution._")
    return "\n".join(lines)


def format_next_best_action(ctx: dict) -> str:
    c = ctx["customer"]
    holdings = ctx.get("holdings", [])
    tasks = ctx.get("tasks", [])
    interactions = ctx.get("interactions", [])

    lines = [mock_note(ctx.get("is_mock", False))]
    lines.append(f"*Next Best Actions — {c.get('preferred_name') or c.get('full_name')}*")
    lines.append("")

    if tasks:
        lines.append("*Open Tasks from System*")
        for t in tasks:
            lines.append(f"*[{t.get('urgency', 'Medium')}]* {t.get('action_title', '')}")
            lines.append(f"  {t.get('action_detail', '')}")
            lines.append(f"  Due: {t.get('due_date', 'TBD')} | {t.get('compliance_note') or ''}")
            lines.append("")
    else:
        lines.append("*No open tasks on file.*")
        lines.append("")

    # Derive simple observations
    lines.append("*Observations*")

    # Concentration flag
    sectors: dict = {}
    for h in holdings:
        s = h.get("sector", "Other")
        sectors[s] = sectors.get(s, 0) + float(h.get("portfolio_weight_pct", 0))
    for sector, pct in sectors.items():
        if pct > 20:
            lines.append(f"- ⚠️ {sector} concentration at {pct:.1f}% — consider discussing rebalancing")

    # Follow-up check
    pending = [i for i in interactions if i.get("follow_up_required", "").lower() == "yes"]
    if pending:
        lines.append(f"- 🔔 {len(pending)} interaction(s) with unresolved follow-ups")

    # Review due
    next_due = c.get("next_review_due", "")
    if next_due:
        lines.append(f"- 📅 Next suitability review due: {next_due}")

    lines.append("")
    lines.append("_Internal RM use only. Not for client distribution._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# V3 — Equity Research Plugin fallbacks
# Used when Claude API is unavailable. Returns structured template output.
# ---------------------------------------------------------------------------

def _mock_banner_equity(ctx: dict) -> str:
    label = ctx.get("source_label", "MOCK / NOT REAL-TIME")
    return f"⚠️ *{label}*\n\n"


def format_earnings_deep_dive(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    earnings = ctx.get("earnings", {})
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Earnings Deep Dive — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | {snap.get('geography', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    if earnings:
        lines.append(f"- {earnings.get('quarter', 'N/A')}: Revenue {earnings.get('revenue_actual', 'N/A')} vs est {earnings.get('revenue_est', 'N/A')} — {earnings.get('beat_miss', 'N/A')}")
        lines.append(f"- EPS {earnings.get('eps_actual', 'N/A')} vs est {earnings.get('eps_est', 'N/A')} | Guidance: {earnings.get('guidance_direction', 'N/A')}")
        lines.append(f"- Management tone: {earnings.get('mgmt_tone', 'N/A')}")
    else:
        lines.append("- Earnings data not available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    if catalysts:
        lines.append(f"- Key near-term catalyst: {catalysts[0]}")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_stock_catalyst(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    thesis = ctx.get("thesis", {})
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Stock Catalyst — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | Conviction: {thesis.get('conviction', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    for c in catalysts[:3]:
        lines.append(f"- {c}")
    if not catalysts:
        lines.append("- No catalyst data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append(f"- Use these catalysts to frame a forward-looking conversation about {ticker}.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_thesis_check(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    thesis = ctx.get("thesis", {})
    risks = ctx.get("risks", [])
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Thesis Check — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | Conviction: {thesis.get('conviction', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    if thesis.get("bull_case"):
        lines.append(f"- Bull: {thesis['bull_case']}")
    if thesis.get("bear_case"):
        lines.append(f"- Bear: {thesis['bear_case']}")
    if not thesis:
        lines.append("- No thesis data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append(f"- Raise {ticker} when conviction is High and client mandate aligns with the bull case.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_idea_generation(ctx: dict) -> str:
    ideas = ctx.get("ideas", [])
    profile = ctx.get("client_profile", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Idea Generation — {profile.get('name', 'Client')}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {profile.get('risk_profile', 'N/A')} | {profile.get('objective', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    for idea in ideas[:3]:
        snap = idea.get("snapshot", {})
        conviction = idea.get("conviction", "N/A")
        lines.append(f"- {idea['ticker']} ({snap.get('sector', 'N/A')}) — Conviction: {conviction}")
        if idea.get("catalysts"):
            lines.append(f"  Key catalyst: {idea['catalysts'][0]}")
    if not ideas:
        lines.append("- No ideas available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    lines.append("- Validate each idea against client suitability before raising. Use /thesis_check [ticker] for detail.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append("- Present ideas as conversation starters, not recommendations.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_morning_note(ctx: dict) -> str:
    ticker = ctx.get("ticker", "")
    catalysts = ctx.get("catalysts", [])
    risks = ctx.get("risks", [])
    thesis = ctx.get("thesis", {})
    snap = ctx.get("snapshot", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Morning Note — {ticker}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {snap.get('name', ticker)} | {snap.get('sector', 'N/A')} | {snap.get('geography', 'N/A')}")
    if snap.get("description"):
        desc = snap["description"]
        lines.append(f"- {desc[:120]}{'...' if len(desc) > 120 else ''}")
    lines.append("")
    lines.append("*Key Observations*")
    for c in catalysts[:3]:
        lines.append(f"- {c}")
    if not catalysts:
        lines.append("- No catalyst data available.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    for r in risks[:2]:
        lines.append(f"- {r}")
    if not risks:
        lines.append("- No risk data available.")
    lines.append("")
    lines.append("*RM Framing*")
    conviction = thesis.get("conviction", "N/A")
    lines.append(f"- Internal conviction: {conviction}. Surface this in morning client touchpoints where mandate allows.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)


def format_portfolio_scenario(ctx: dict) -> str:
    client_name = ctx.get("client_name", "Client")
    scenarios_by_ticker = ctx.get("scenarios_by_ticker", [])
    profile = ctx.get("profile", {})

    lines = [_mock_banner_equity(ctx)]
    lines.append(f"*Portfolio Scenario — {client_name}*")
    lines.append("")
    lines.append("*Snapshot*")
    lines.append(f"- {profile.get('risk_profile', 'N/A')} | {profile.get('objective', 'N/A')}")
    lines.append("")
    lines.append("*Key Observations*")
    shown = 0
    for item in scenarios_by_ticker:
        if shown >= 3:
            break
        ticker = item.get("ticker", "")
        for s in item.get("scenarios", [])[:1]:
            lines.append(f"- {ticker}: {s['name']} — {s['impact']}. {s['note']}")
            shown += 1
    if shown == 0:
        lines.append("- No scenario data available for current holdings.")
    lines.append("")
    lines.append("*Key Risks / Watchouts*")
    lines.append("- Review concentration in high-impact scenario names before next client meeting.")
    lines.append("")
    lines.append("*RM Framing*")
    lines.append("- Frame scenarios as preparedness, not predictions. Focus on what the RM can action now.")
    lines.append("_Internal RM use only. Not investment advice._")
    return "\n".join(lines)
