"""
services/relationship_memory_service.py

Shared Relationship Memory Layer for Aureus RM Copilot.

Responsibilities:
  - Retrieve and summarize relationship context from Google Sheets
  - Own in-process session state per chat_id (last client, ticker, intent)
  - Return structured context dicts — never raw data dumps

Session state is updated by AureusOrchestrator / CommandRouter after every
successful command resolution, not by ChatRouter.

ChatRouter reads session state to fill missing args in follow-up queries
(e.g. "What about DBS?" after a John Tan session).
"""

import logging
from datetime import date, timedelta
from typing import Optional

from services.sheets_service import SheetsService

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK_DAYS = 90
_STALE_CONTACT_DAYS = 30


class RelationshipMemoryService:
    """
    Shared infrastructure layer for relationship context and session continuity.

    Not an agent — this is a service that all agents and the orchestrator
    can call to retrieve structured relationship signals.
    """

    def __init__(self, sheets: Optional[SheetsService]):
        self.sheets = sheets
        # {chat_id: {last_client_name, last_client_id, last_ticker, last_intent, last_command}}
        self._session_store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Session continuity — owned here
    # ------------------------------------------------------------------

    def get_session_state(self, chat_id: str) -> dict:
        """Return current session state for a chat_id. Returns empty dict if none."""
        return dict(self._session_store.get(str(chat_id), {}))

    def update_session_state(self, chat_id: str, **kwargs) -> None:
        """
        Update session state after a successful command execution.
        Called by AureusOrchestrator or CommandRouter — never by ChatRouter.
        """
        cid = str(chat_id)
        if cid not in self._session_store:
            self._session_store[cid] = {}
        self._session_store[cid].update(kwargs)
        logger.debug(
            "Session updated | chat_id=%s fields=%s", cid, list(kwargs.keys())
        )

    def clear_session_state(self, chat_id: str) -> None:
        """Reset session state for a chat_id."""
        self._session_store.pop(str(chat_id), None)

    # ------------------------------------------------------------------
    # Relationship context retrieval (returns structured dicts)
    # ------------------------------------------------------------------

    def get_recent_relationship_context(
        self, customer_id: str, days: int = _DEFAULT_LOOKBACK_DAYS
    ) -> dict:
        """
        Return structured relationship context for the last N days.
        Never dumps raw rows — returns distilled signals.
        """
        if not self.sheets:
            return self._mock_relationship_context()

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        all_interactions = self.sheets.list_customer_interactions(
            customer_id, limit=20
        )
        recent = [
            i for i in all_interactions
            if str(i.get("interaction_date", "")) >= cutoff
        ]
        tasks = self.sheets.list_open_tasks(customer_id)

        last_interaction = recent[0] if recent else None
        return {
            "customer_id": customer_id,
            "lookback_days": days,
            "interaction_count": len(recent),
            "recent_interactions": self._distill_interactions(recent[:5]),
            "open_tasks": self._distill_tasks(tasks),
            "last_interaction_date": (
                last_interaction.get("interaction_date") if last_interaction else None
            ),
            "last_interaction_type": (
                last_interaction.get("interaction_type") if last_interaction else None
            ),
        }

    def get_open_followups(self, customer_id: str) -> list[dict]:
        """Return all open follow-up tasks for a customer."""
        if not self.sheets:
            return []
        tasks = self.sheets.list_open_tasks(customer_id)
        return [
            {
                "task_id": t.get("task_id"),
                "title": t.get("action_title"),
                "task_type": t.get("task_type"),
                "urgency": t.get("urgency"),
                "due_date": t.get("due_date"),
                "rationale": t.get("rationale"),
                "linked_ticker": t.get("linked_ticker", ""),
            }
            for t in tasks
            if str(t.get("follow_up_required", "")).lower() == "yes"
            or str(t.get("task_type", "")).lower() in ("follow-up", "followup")
        ]

    def get_overdue_followups(self, customer_id: str) -> list[dict]:
        """Return tasks with due_date < today for a customer, sorted by days overdue."""
        if not self.sheets:
            return []
        today_str = date.today().isoformat()
        tasks = self.sheets.list_open_tasks(customer_id)
        overdue = []
        for t in tasks:
            due = str(t.get("due_date", "")).strip()
            if due and due < today_str:
                try:
                    days_overdue = (date.today() - date.fromisoformat(due)).days
                except (ValueError, TypeError):
                    days_overdue = 0
                overdue.append({
                    "task_id": t.get("task_id"),
                    "title": t.get("action_title"),
                    "task_type": t.get("task_type"),
                    "urgency": t.get("urgency"),
                    "due_date": due,
                    "days_overdue": days_overdue,
                    "rationale": t.get("rationale", ""),
                    "linked_ticker": t.get("linked_ticker", ""),
                })
        return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)

    def get_last_discussed_topics(self, customer_id: str) -> list[str]:
        """Return tickers and themes mentioned in recent interactions."""
        if not self.sheets:
            return ["DBS", "tech exposure", "structured notes"]
        interactions = self.sheets.list_customer_interactions(customer_id, limit=10)
        topics: set[str] = set()
        for i in interactions:
            for field in ("discussion_tickers", "discussion_themes", "key_topics"):
                raw = str(i.get(field, "")).strip()
                for item in raw.split(","):
                    item = item.strip()
                    if item and item.lower() not in ("", "none", "n/a"):
                        topics.add(item)
        return list(topics)[:10]

    def get_last_recommendations(self, customer_id: str) -> list[dict]:
        """Return recommendation history with status and client response."""
        if not self.sheets:
            return []
        interactions = self.sheets.list_customer_interactions(customer_id, limit=20)
        recs = []
        for i in interactions:
            rec = str(i.get("recommendation_given", "")).strip()
            if rec and rec.lower() not in ("", "no", "none", "n/a"):
                recs.append({
                    "date": i.get("interaction_date"),
                    "recommendation": rec,
                    "status": i.get("recommendation_status", "Pending"),
                    "client_response": i.get("client_response", "Pending"),
                    "interaction_type": i.get("interaction_type"),
                })
        return recs

    def get_client_response_history(self, customer_id: str) -> list[dict]:
        """Return logged client responses (interested / neutral / declined)."""
        if not self.sheets:
            return []
        interactions = self.sheets.list_customer_interactions(customer_id, limit=20)
        return [
            {
                "date": i.get("interaction_date"),
                "topic": i.get("discussion_tickers") or i.get("interaction_type", ""),
                "client_response": i.get("client_response", ""),
            }
            for i in interactions
            if str(i.get("client_response", "")).strip()
            and str(i.get("client_response", "")).strip().lower()
            not in ("", "pending")
        ]

    def summarize_relationship_state(self, customer_id: str) -> dict:
        """
        Return a compact relationship summary for agent prompt injection.
        Structured signals only — no raw row dumps.
        """
        if not self.sheets:
            return self._mock_relationship_context()

        try:
            ctx = self.get_recent_relationship_context(customer_id)
            overdue = self.get_overdue_followups(customer_id)
            recs = self.get_last_recommendations(customer_id)
            topics = self.get_last_discussed_topics(customer_id)

            # Days since last contact
            days_since_contact: Optional[int] = None
            last_date = ctx.get("last_interaction_date")
            if last_date:
                try:
                    days_since_contact = (
                        date.today() - date.fromisoformat(str(last_date))
                    ).days
                except (ValueError, TypeError):
                    pass

            pending_recs = [
                r for r in recs
                if str(r.get("client_response", "")).lower() in ("pending", "")
            ]

            return {
                "last_interaction_date": last_date,
                "days_since_last_contact": days_since_contact,
                "last_interaction_type": ctx.get("last_interaction_type"),
                "recent_interaction_count": ctx.get("interaction_count", 0),
                "recent_interactions": ctx.get("recent_interactions", []),
                "overdue_tasks": overdue,
                "overdue_count": len(overdue),
                "open_tasks": ctx.get("open_tasks", []),
                "open_task_count": len(ctx.get("open_tasks", [])),
                "last_discussed_topics": topics[:5],
                "last_recommendations": recs[:3],
                "pending_recommendations": pending_recs[:3],
            }
        except Exception as exc:
            logger.warning(
                "RelationshipMemoryService: failed to summarize state for %s: %s",
                customer_id, exc,
            )
            return {}

    def get_last_review_date(self, customer_id: str) -> Optional[str]:
        """Return last_review_date from the customer record."""
        if not self.sheets:
            return None
        customer = self.sheets.get_customer_by_id(customer_id)
        return str(customer.get("last_review_date", "")) if customer else None

    def get_next_review_due(self, customer_id: str) -> Optional[str]:
        """Return next_review_due from the customer record."""
        if not self.sheets:
            return None
        customer = self.sheets.get_customer_by_id(customer_id)
        return str(customer.get("next_review_due", "")) if customer else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _distill_interactions(self, interactions: list[dict]) -> list[dict]:
        return [
            {
                "date": i.get("interaction_date"),
                "type": i.get("interaction_type"),
                "channel": i.get("channel"),
                "summary": str(i.get("summary", ""))[:200],
                "discussion_tickers": i.get("discussion_tickers", ""),
                "recommendation_given": i.get("recommendation_given", ""),
                "client_response": i.get("client_response", ""),
                "follow_up_required": i.get("follow_up_required"),
                "follow_up_due": i.get("follow_up_due"),
            }
            for i in interactions
        ]

    def _distill_tasks(self, tasks: list[dict]) -> list[dict]:
        today_str = date.today().isoformat()
        return [
            {
                "task_id": t.get("task_id"),
                "title": t.get("action_title"),
                "type": t.get("task_type"),
                "urgency": t.get("urgency"),
                "due_date": t.get("due_date"),
                "is_overdue": bool(
                    t.get("due_date") and str(t.get("due_date", "")) < today_str
                ),
                "linked_ticker": t.get("linked_ticker", ""),
            }
            for t in tasks
        ]

    def _mock_relationship_context(self) -> dict:
        """Minimal mock context for dev/test mode when Sheets is unavailable."""
        return {
            "last_interaction_date": "2024-11-15",
            "days_since_last_contact": 150,
            "last_interaction_type": "Portfolio Review",
            "recent_interaction_count": 2,
            "recent_interactions": [
                {
                    "date": "2024-11-15",
                    "type": "Portfolio Review",
                    "channel": "Phone",
                    "summary": "Quarterly review. Client happy with DBS performance. Queried about adding more tech exposure.",
                    "discussion_tickers": "DBS",
                    "recommendation_given": "",
                    "client_response": "",
                    "follow_up_required": "Yes",
                    "follow_up_due": "2024-12-01",
                },
            ],
            "overdue_tasks": [
                {
                    "task_id": "T001",
                    "title": "Send tech exposure options",
                    "task_type": "Follow-up",
                    "urgency": "Medium",
                    "due_date": "2024-12-15",
                    "days_overdue": 120,
                    "rationale": "Client expressed interest in tech during Nov review",
                    "linked_ticker": "",
                }
            ],
            "overdue_count": 1,
            "open_tasks": [
                {
                    "task_id": "T001",
                    "title": "Send tech exposure options",
                    "type": "Follow-up",
                    "urgency": "Medium",
                    "due_date": "2024-12-15",
                    "is_overdue": True,
                    "linked_ticker": "",
                }
            ],
            "open_task_count": 1,
            "last_discussed_topics": ["DBS", "tech exposure", "structured notes"],
            "last_recommendations": [],
            "pending_recommendations": [],
        }
