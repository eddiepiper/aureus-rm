"""
services/nba_agent.py

NBA Agent — Next Best Action reasoning layer for Aureus RM Copilot.

Architecture:
  Step 1: Rule-based signal scoring (deterministic, explainable)
  Step 2: Single Claude call to produce "Why Now" narrative + RM Framing

Scored actions include: score, reason_codes, confidence, source_signals

This is an internal specialist — users never interact with it directly.
All outputs are synthesised into a single Aureus response.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from services.claude_service import SYSTEM_PROMPT as AUREUS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal scores — rule-based, deterministic
# ---------------------------------------------------------------------------

SIGNAL_SCORES: dict[str, int] = {
    "OVERDUE_TASK":            30,
    "UPCOMING_REVIEW":         25,  # review due within 7 days
    "IDLE_CASA":               20,  # deployable cash >= 5% of portfolio
    "PENDING_RECOMMENDATION":  15,  # recommendation given, client_response = Pending
    "NO_RECENT_CONTACT":       10,  # last contact > 30 days
    "CONCENTRATION_RISK":      10,  # open task mentions concentration
    "OPEN_WATCHLIST":           8,  # watchlist item not yet actioned
    "OPEN_TASK":                5,  # any non-overdue open task
}

_REVIEW_HORIZON_DAYS = 7
_STALE_CONTACT_DAYS = 30
_IDLE_CASA_MIN_PCT = 5.0

# ---------------------------------------------------------------------------
# Per-command Claude prompts — NBA Agent uses generate_raw()
# ---------------------------------------------------------------------------

_NBA_PROMPTS: dict[str, str] = {
    "next-best-action": """\
Prepare a Next Best Action brief for {client_name}.

Relationship context:
{relationship_json}

Portfolio context (compressed):
{portfolio_json}

Ranked actions (rule-based scoring):
{scored_actions_json}

Use the four-section Aureus format:

*Snapshot* — One precise line: who this client is, where the relationship stands right now.

*Top 3 Next Actions* — List exactly 3 actions in priority order. For each:
  - Action title (bold)
  - Why now: the specific signal — days overdue, CASA amount, recommendation date, days since contact
  - RM opening: one sentence on how to raise this in a conversation

*Key Risks* — 2 bullets: what is the commercial and relationship cost of inaction this week.

*RM Framing* — 2–3 lines: what the RM must do in the next 5 business days. Specific, ordered, actionable.

Ground every action in the scored signals. No generic filler. Use actual dates, amounts, and task titles.
""",

    "relationship-status": """\
Prepare a Relationship Status brief for {client_name}.

Relationship context:
{relationship_json}

Portfolio context (compressed):
{portfolio_json}

Use the four-section Aureus format:

*Snapshot* — Client overview: mandate, segment, and the single most important relationship signal now.

*Recent Relationship Activity* — 2–3 bullets: what was discussed, what Aureus or the RM recommended, what the client's response trajectory looks like.

*Open Follow-Ups* — 2 bullets: what is still outstanding, how overdue each item is, what was originally agreed.

*Key Watchout* — 1 bullet: the highest-risk item in the relationship right now.

*Suggested Next Step* — What the RM must do, and why timing matters. One specific action.

Use actual dates, task titles, and tickers from the context.
""",

    "overdue-followups": """\
Prepare an Overdue Follow-Ups brief for {client_name}.

Overdue items:
{overdue_json}

Relationship context:
{relationship_json}

Use the four-section Aureus format:

*Snapshot* — How many items are overdue, how long the longest has been outstanding, and the most urgent one.

*Overdue Items* — One bullet per overdue item: task title, days overdue, original rationale.

*Why They Matter* — 2 bullets: what is the relationship or commercial consequence of each overdue item remaining unresolved.

*Suggested RM Action* — Exactly what the RM should do in the next 48 hours to resolve or escalate. Be specific — name the task, the client, and the expected outcome.

Use actual task titles, due dates, and days overdue from the context.
""",

    "attention-list": """\
Prepare the RM Attention List.

Scored clients (rule-based urgency ranking, top 5):
{scored_clients_json}

Today: {today}

Use this format (not the standard four sections):

*Attention List — {today}*

For each client in rank order:

*[Rank]. [Client Name]* — Urgency: [High/Medium/Low]
- Why now: the 1–2 signals driving this client to the top of the list
- Action: one specific next step the RM should take this week

After listing all clients:

*RM Priority Today*
1–2 sentences on where to focus first and why one client is most time-sensitive.

Be concise. Use actual client names, task titles, and signal types. No generic filler.
End with: _For internal RM use only. Not investment advice._
""",

    "morning-rm-brief": """\
Prepare the Morning RM Brief.

Priority clients today (rule-based ranking):
{scored_clients_json}

Today: {today}

Use this format:

*Morning RM Brief — {today}*

*Priority Clients Today*
Top 3 clients the RM should contact today. For each: name + one-line rationale (the signal driving urgency).

*Overdue Items*
Any tasks past their due date across the book. Format: Client name — task title — days overdue.

*Deployment Opportunities*
Clients with idle CASA or deployable liquidity. Format: Client name — amount and currency.

*Suggested Actions*
3 specific actions the RM should take today, ordered by priority.

Be precise and commercially useful. Ground every point in the ranked signals.
End with: _For internal RM use only. Not investment advice._
""",
}


class NBAAgent:
    """
    Next Best Action reasoning layer.

    Hybrid approach:
      1. Deterministic rule-based scoring → ranked ScoredAction list
      2. Single Claude call → Aureus-formatted narrative with explainability

    Implements the same generate(command, ctx) interface as other agents.
    """

    def __init__(self, claude_service, relationship_memory=None):
        self.claude = claude_service
        self.relationship_memory = relationship_memory
        logger.info("NBAAgent: ready")

    # ------------------------------------------------------------------
    # Main entry point — called by AureusOrchestrator
    # ------------------------------------------------------------------

    async def generate(self, command: str, ctx: dict) -> str:
        """
        Generate a unified Aureus response for an NBA command.
        """
        is_mock = ctx.get("is_mock", False)
        dispatch = {
            "next-best-action":    self._cmd_next_best_action,
            "relationship-status": self._cmd_relationship_status,
            "overdue-followups":   self._cmd_overdue_followups,
            "attention-list":      self._cmd_attention_list,
            "morning-rm-brief":    self._cmd_morning_rm_brief,
        }
        handler = dispatch.get(command)
        if handler is None:
            logger.warning("NBAAgent: unknown command %s", command)
            return f"❌ NBA Agent does not handle command: `{command}`"
        return await handler(ctx, is_mock)

    async def analyze(self, command: str, ctx: dict) -> str:
        """
        Return brief analytical bullets for orchestrator synthesis flows.
        Used when NBAAgent collaborates with Portfolio Counsellor on next-best-action.
        Max 500 tokens — raw bullets, no formatting.
        """
        relationship_ctx = ctx.get("relationship_context", {})
        scored = self.rank_next_actions(ctx)

        prompt = (
            f"NBA signal analysis for next-best-action.\n\n"
            f"Top scored actions:\n"
            f"{json.dumps(scored[:3], indent=2, default=str)}\n\n"
            f"Relationship context summary:\n"
            f"{json.dumps(relationship_ctx, indent=2, default=str)}\n\n"
            "Provide 3–4 concise analytical bullets:\n"
            "- What signals are driving urgency\n"
            "- What is the most time-sensitive action and why\n"
            "- What is the relationship risk of inaction\n"
            "No section headers. Raw bullets only."
        )

        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=ctx.get("is_mock", False),
            max_tokens=500,
        )

    # ------------------------------------------------------------------
    # Signal scoring — deterministic, returns structured ScoredAction objects
    # ------------------------------------------------------------------

    def score_customer(
        self,
        customer: dict,
        relationship_ctx: dict,
        portfolio_ctx: dict,
    ) -> dict:
        """
        Score a single customer based on urgency signals.

        Returns a dict with:
          - score: int (cumulative signal score)
          - reason_codes: list[str] (signal identifiers)
          - confidence: str ("high" | "medium" | "low")
          - source_signals: dict (raw values driving each reason code)
        """
        score = 0
        reason_codes: list[str] = []
        source_signals: dict = {}

        # 1. Overdue tasks — highest weight, up to 2 tasks counted
        overdue_tasks = relationship_ctx.get("overdue_tasks", [])
        if overdue_tasks:
            count = min(len(overdue_tasks), 2)
            score += SIGNAL_SCORES["OVERDUE_TASK"] * count
            reason_codes.append("OVERDUE_TASK")
            source_signals["overdue_tasks"] = [
                {"title": t.get("title"), "days_overdue": t.get("days_overdue")}
                for t in overdue_tasks[:2]
            ]

        # 2. Upcoming review
        next_review = str(customer.get("next_review_due", "")).strip()
        if next_review:
            try:
                review_date = date.fromisoformat(next_review)
                days_to_review = (review_date - date.today()).days
                if 0 <= days_to_review <= _REVIEW_HORIZON_DAYS:
                    score += SIGNAL_SCORES["UPCOMING_REVIEW"]
                    reason_codes.append("UPCOMING_REVIEW")
                    source_signals["days_to_review"] = days_to_review
                    source_signals["review_date"] = next_review
            except (ValueError, TypeError):
                pass

        # 3. Idle CASA / deployable liquidity
        liquidity = portfolio_ctx.get("liquidity")
        if liquidity:
            casa_pct = _safe_float(liquidity.get("total_deployable_pct"))
            if casa_pct >= _IDLE_CASA_MIN_PCT:
                score += SIGNAL_SCORES["IDLE_CASA"]
                reason_codes.append("IDLE_CASA")
                source_signals["casa_pct"] = casa_pct
                source_signals["casa_holdings"] = liquidity.get("holdings", [])

        # 4. Pending recommendations (no client response yet)
        pending_recs = relationship_ctx.get("pending_recommendations", [])
        if pending_recs:
            count = min(len(pending_recs), 2)
            score += SIGNAL_SCORES["PENDING_RECOMMENDATION"] * count
            reason_codes.append("PENDING_RECOMMENDATION")
            source_signals["pending_recs"] = [
                {"rec": r.get("recommendation"), "date": r.get("date")}
                for r in pending_recs[:2]
            ]

        # 5. Stale contact
        days_since = relationship_ctx.get("days_since_last_contact")
        if days_since is not None and days_since > _STALE_CONTACT_DAYS:
            score += SIGNAL_SCORES["NO_RECENT_CONTACT"]
            reason_codes.append("NO_RECENT_CONTACT")
            source_signals["days_since_contact"] = days_since

        # 6. Non-overdue open tasks
        open_tasks = relationship_ctx.get("open_tasks", [])
        non_overdue = [t for t in open_tasks if not t.get("is_overdue")]
        if non_overdue:
            score += SIGNAL_SCORES["OPEN_TASK"] * min(len(non_overdue), 3)
            reason_codes.append("OPEN_TASK")
            source_signals["open_task_count"] = len(non_overdue)

        # 7. Concentration risk — task title mentions concentration/overweight/exposure
        all_tasks = overdue_tasks + open_tasks
        for task in all_tasks:
            title = str(task.get("title", "")).lower()
            if any(kw in title for kw in ("concentration", "overweight", "exposure")):
                score += SIGNAL_SCORES["CONCENTRATION_RISK"]
                reason_codes.append("CONCENTRATION_RISK")
                source_signals["concentration_task"] = task.get("title")
                break  # only count once

        # 8. Open watchlist items not yet actioned
        watchlist_items = relationship_ctx.get("watchlist_items", [])
        if watchlist_items:
            count = min(len(watchlist_items), 2)
            score += SIGNAL_SCORES["OPEN_WATCHLIST"] * count
            reason_codes.append("OPEN_WATCHLIST")
            source_signals["watchlist_count"] = len(watchlist_items)

        confidence = "high" if score >= 50 else "medium" if score >= 25 else "low"

        return {
            "customer_id": customer.get("customer_id"),
            "client_name": (
                customer.get("full_name") or customer.get("preferred_name", "Unknown")
            ),
            "score": score,
            "reason_codes": reason_codes,
            "confidence": confidence,
            "source_signals": source_signals,
        }

    def rank_next_actions(self, ctx: dict) -> list[dict]:
        """
        Convert a combined context dict into a ranked list of scored actions.
        Used for single-client NBA commands.

        Returns up to 3 scored actions, sorted by score descending.
        Each action includes: title, action_detail, rationale, score,
        urgency, reason_codes, confidence, source_signals, linked_ticker, due_date.
        """
        relationship_ctx = ctx.get("relationship_context", {})
        actions: list[dict] = []

        # Overdue tasks → highest priority
        for task in relationship_ctx.get("overdue_tasks", [])[:3]:
            days_over = task.get("days_overdue", 0)
            actions.append({
                "title": task.get("title", "Resolve overdue task"),
                "action_detail": f"Task overdue by {days_over} days (due: {task.get('due_date')})",
                "rationale": task.get("rationale", ""),
                "score": SIGNAL_SCORES["OVERDUE_TASK"] + min(days_over, 30),
                "urgency": "High",
                "reason_codes": ["OVERDUE_TASK"],
                "confidence": "high",
                "source_signals": {
                    "task_title": task.get("title"),
                    "days_overdue": days_over,
                    "due_date": task.get("due_date"),
                },
                "linked_ticker": task.get("linked_ticker", ""),
                "due_date": task.get("due_date", ""),
            })

        # Idle CASA deployment
        liquidity = ctx.get("liquidity")
        if liquidity:
            casa_pct = _safe_float(liquidity.get("total_deployable_pct"))
            if casa_pct >= _IDLE_CASA_MIN_PCT:
                detail_parts = [
                    f"{h.get('currency', '')} {h.get('market_value', '')}"
                    for h in liquidity.get("holdings", [])
                ]
                detail_str = ", ".join(detail_parts) if detail_parts else f"{casa_pct:.0f}% of portfolio"
                actions.append({
                    "title": f"Initiate deployment conversation — {casa_pct:.0f}% idle liquidity",
                    "action_detail": f"Client holds {detail_str} in deployable cash with no current deployment plan",
                    "rationale": "Idle CASA represents a commercial opportunity and a relationship touchpoint",
                    "score": SIGNAL_SCORES["IDLE_CASA"],
                    "urgency": "Medium",
                    "reason_codes": ["IDLE_CASA"],
                    "confidence": "high",
                    "source_signals": {"casa_pct": casa_pct, "casa_detail": detail_str},
                    "linked_ticker": "",
                    "due_date": (date.today() + timedelta(days=14)).isoformat(),
                })

        # Pending recommendations
        for rec in relationship_ctx.get("pending_recommendations", [])[:2]:
            actions.append({
                "title": f"Follow up: {rec.get('recommendation', 'prior recommendation')}",
                "action_detail": (
                    f"Recommendation made on {rec.get('date', 'unknown date')} — "
                    "no client response recorded"
                ),
                "rationale": "Outstanding recommendation without client response — close the loop",
                "score": SIGNAL_SCORES["PENDING_RECOMMENDATION"],
                "urgency": "Medium",
                "reason_codes": ["PENDING_RECOMMENDATION"],
                "confidence": "medium",
                "source_signals": {
                    "recommendation": rec.get("recommendation"),
                    "date": rec.get("date"),
                },
                "linked_ticker": "",
                "due_date": (date.today() + timedelta(days=7)).isoformat(),
            })

        # Stale relationship
        days_since = relationship_ctx.get("days_since_last_contact")
        if days_since is not None and days_since > _STALE_CONTACT_DAYS:
            actions.append({
                "title": f"Re-engage — {days_since} days since last contact",
                "action_detail": f"No recorded interaction in {days_since} days",
                "rationale": "Proactive re-engagement maintains relationship quality and commercial flow",
                "score": SIGNAL_SCORES["NO_RECENT_CONTACT"],
                "urgency": "Low",
                "reason_codes": ["NO_RECENT_CONTACT"],
                "confidence": "medium",
                "source_signals": {"days_since_contact": days_since},
                "linked_ticker": "",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            })

        actions.sort(key=lambda a: a["score"], reverse=True)
        return actions[:3]

    def score_all_customers(
        self,
        all_customers: list[dict],
    ) -> list[dict]:
        """
        Score all customers for the attention list / morning brief.
        Each entry in all_customers must include:
          - customer: dict (customer record)
          - relationship_ctx: dict (from RelationshipMemoryService)
          - portfolio_ctx: dict (compressed holdings, can be sparse)

        Returns top 5 by score, sorted descending.
        """
        scored: list[dict] = []
        for entry in all_customers:
            customer = entry.get("customer", {})
            relationship_ctx = entry.get("relationship_ctx", {})
            portfolio_ctx = entry.get("portfolio_ctx", {})
            scored_customer = self.score_customer(customer, relationship_ctx, portfolio_ctx)
            scored_customer["next_review_due"] = customer.get("next_review_due", "")
            scored_customer["last_interaction_date"] = relationship_ctx.get("last_interaction_date")
            scored_customer["open_task_count"] = relationship_ctx.get("open_task_count", 0)
            scored_customer["overdue_count"] = relationship_ctx.get("overdue_count", 0)
            scored.append(scored_customer)

        scored.sort(key=lambda s: s["score"], reverse=True)
        return scored[:5]

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    async def _cmd_next_best_action(self, ctx: dict, is_mock: bool) -> str:
        scored_actions = self.rank_next_actions(ctx)
        client_name = _extract_client_name(ctx)
        relationship_ctx = ctx.get("relationship_context", {})
        portfolio_ctx = {k: v for k, v in ctx.items() if k != "relationship_context"}

        prompt = _NBA_PROMPTS["next-best-action"].format(
            client_name=client_name,
            relationship_json=json.dumps(relationship_ctx, indent=2, default=str),
            portfolio_json=json.dumps(portfolio_ctx, indent=2, default=str),
            scored_actions_json=json.dumps(scored_actions, indent=2, default=str),
        )
        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=is_mock,
        )

    async def _cmd_relationship_status(self, ctx: dict, is_mock: bool) -> str:
        client_name = _extract_client_name(ctx)
        relationship_ctx = ctx.get("relationship_context", {})
        portfolio_ctx = {k: v for k, v in ctx.items() if k != "relationship_context"}

        prompt = _NBA_PROMPTS["relationship-status"].format(
            client_name=client_name,
            relationship_json=json.dumps(relationship_ctx, indent=2, default=str),
            portfolio_json=json.dumps(portfolio_ctx, indent=2, default=str),
        )
        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=is_mock,
        )

    async def _cmd_overdue_followups(self, ctx: dict, is_mock: bool) -> str:
        client_name = _extract_client_name(ctx)
        relationship_ctx = ctx.get("relationship_context", {})
        overdue = relationship_ctx.get("overdue_tasks", [])

        if not overdue and not is_mock:
            return (
                f"*No overdue items for {client_name}.*\n\n"
                "All open tasks are within their due dates. "
                "Use /next\\_best\\_action to see what to prioritise this week.\n\n"
                "_For internal RM use only. Not investment advice._"
            )

        prompt = _NBA_PROMPTS["overdue-followups"].format(
            client_name=client_name,
            overdue_json=json.dumps(overdue, indent=2, default=str),
            relationship_json=json.dumps(relationship_ctx, indent=2, default=str),
        )
        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=is_mock,
        )

    async def _cmd_attention_list(self, ctx: dict, is_mock: bool) -> str:
        scored_clients = ctx.get("scored_clients", [])
        today_str = date.today().strftime("%d %b %Y")

        if not scored_clients:
            return (
                f"*Attention List — {today_str}*\n\n"
                "No clients flagged for immediate attention.\n\n"
                "_For internal RM use only. Not investment advice._"
            )

        prompt = _NBA_PROMPTS["attention-list"].format(
            scored_clients_json=json.dumps(scored_clients, indent=2, default=str),
            today=today_str,
        )
        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=is_mock,
        )

    async def _cmd_morning_rm_brief(self, ctx: dict, is_mock: bool) -> str:
        scored_clients = ctx.get("scored_clients", [])
        today_str = date.today().strftime("%d %b %Y")

        prompt = _NBA_PROMPTS["morning-rm-brief"].format(
            scored_clients_json=json.dumps(scored_clients, indent=2, default=str),
            today=today_str,
        )
        return await self.claude.generate_raw(
            system_prompt=AUREUS_SYSTEM_PROMPT,
            user_prompt=prompt,
            is_mock=is_mock,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_client_name(ctx: dict) -> str:
    profile = ctx.get("profile") or ctx.get("customer", {})
    return (
        profile.get("name")
        or profile.get("preferred_name")
        or profile.get("full_name")
        or ctx.get("client_profile", {}).get("name")
        or "the client"
    )


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
