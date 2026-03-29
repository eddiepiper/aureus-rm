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
