"""
services/writeback_service.py

Safe, non-blocking write-back layer for Aureus RM Copilot.

Responsibilities:
  - Append interaction logs to Google Sheets
  - Create follow-up tasks with duplicate detection
  - Never block user-facing responses (fire-and-forget via asyncio.create_task)
  - Timeout protection on all writes (10s)
  - Structured warning logging on failure

Duplicate key format:
  {customer_id}:{task_category}:{linked_ticker_or_none}:{intent_family}

Examples:
  CUST001:followup:NVDA:idea_generation
  CUST001:review:none:meeting_pack
"""

import asyncio
import datetime
import logging
import uuid
from typing import Optional

from services.sheets_service import SheetsService

logger = logging.getLogger(__name__)

_WRITE_TIMEOUT_SECONDS = 10.0

# Map command slugs → human-readable interaction type
_COMMAND_TYPE_MAP: dict[str, str] = {
    "client-review":       "Client Review",
    "meeting-pack":        "Meeting Pack",
    "next-best-action":    "Next Best Action",
    "idea-generation":     "Idea Generation",
    "portfolio-scenario":  "Portfolio Scenario",
    "portfolio-fit":       "Portfolio Fit",
    "relationship-status": "Relationship Status",
    "overdue-followups":   "Overdue Follow-ups",
    "attention-list":      "Attention List",
    "morning-rm-brief":    "Morning RM Brief",
    "log-response":        "Client Response Log",
}


class WritebackService:
    """
    Non-blocking write-back with duplicate-aware task creation.

    All public async methods can be safely fire-and-forgotten with
    asyncio.create_task() — they will never raise into the caller.
    """

    def __init__(self, sheets: Optional[SheetsService]):
        self.sheets = sheets

    # ------------------------------------------------------------------
    # Fire-and-forget schedulers (call from sync context)
    # ------------------------------------------------------------------

    def schedule_interaction_log(
        self,
        customer_id: str,
        command: str,
        response_summary: str,
        **kwargs,
    ) -> None:
        """Schedule an async interaction log without blocking the caller."""
        asyncio.create_task(
            self.append_interaction_log(
                customer_id, command, response_summary, **kwargs
            )
        )

    def schedule_task_creation(
        self,
        customer_id: str,
        action_title: str,
        task_type: str,
        task_category: str,
        intent_family: str,
        linked_ticker: Optional[str] = None,
        action_detail: str = "",
        rationale: str = "",
        urgency: str = "Medium",
        due_date: str = "",
    ) -> None:
        """Schedule async task creation without blocking the caller."""
        asyncio.create_task(
            self.create_followup_task(
                customer_id=customer_id,
                action_title=action_title,
                task_type=task_type,
                task_category=task_category,
                intent_family=intent_family,
                linked_ticker=linked_ticker,
                action_detail=action_detail,
                rationale=rationale,
                urgency=urgency,
                due_date=due_date,
            )
        )

    # ------------------------------------------------------------------
    # Async write methods (with timeout protection)
    # ------------------------------------------------------------------

    async def append_interaction_log(
        self,
        customer_id: str,
        command: str,
        response_summary: str,
        discussion_tickers: str = "",
        recommendation_given: str = "",
        client_response: str = "Pending",
        follow_up_required: str = "No",
        follow_up_due: str = "",
        interaction_type: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Optional[str]:
        """
        Append an interaction log row to Sheets.
        Returns interaction_id on success, None on failure.
        Write-back failures never propagate to the caller.
        """
        if not self.sheets:
            return None
        try:
            loop = asyncio.get_event_loop()
            interaction_id = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._sync_write_interaction(
                        customer_id=customer_id,
                        command=command,
                        response_summary=response_summary,
                        discussion_tickers=discussion_tickers,
                        recommendation_given=recommendation_given,
                        client_response=client_response,
                        follow_up_required=follow_up_required,
                        follow_up_due=follow_up_due,
                        interaction_type=interaction_type,
                        summary=summary,
                    ),
                ),
                timeout=_WRITE_TIMEOUT_SECONDS,
            )
            return interaction_id
        except asyncio.TimeoutError:
            logger.warning(
                "WritebackService: interaction log timed out | customer=%s command=%s",
                customer_id, command,
            )
        except Exception as exc:
            logger.warning(
                "WritebackService: interaction log failed | customer=%s command=%s error=%s",
                customer_id, command, exc,
            )
        return None

    async def create_followup_task(
        self,
        customer_id: str,
        action_title: str,
        task_type: str,
        task_category: str,
        intent_family: str,
        linked_ticker: Optional[str] = None,
        action_detail: str = "",
        rationale: str = "",
        urgency: str = "Medium",
        due_date: str = "",
    ) -> Optional[str]:
        """
        Create a follow-up task with duplicate detection.
        Returns task_id if created, existing task_id if duplicate, None on failure.
        """
        if not self.sheets:
            return None

        duplicate_key = build_duplicate_key(
            customer_id, task_category, linked_ticker, intent_family
        )

        # Check for existing open task with same key before writing
        existing = await self.find_similar_open_task(duplicate_key)
        if existing:
            logger.info(
                "WritebackService: duplicate task skipped | key=%s existing=%s",
                duplicate_key, existing.get("task_id"),
            )
            return existing.get("task_id")

        try:
            loop = asyncio.get_event_loop()
            task_id = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._sync_write_task(
                        customer_id=customer_id,
                        action_title=action_title,
                        task_type=task_type,
                        duplicate_key=duplicate_key,
                        linked_ticker=linked_ticker,
                        action_detail=action_detail,
                        rationale=rationale,
                        urgency=urgency,
                        due_date=due_date,
                    ),
                ),
                timeout=_WRITE_TIMEOUT_SECONDS,
            )
            return task_id
        except asyncio.TimeoutError:
            logger.warning(
                "WritebackService: task creation timed out | customer=%s title=%s",
                customer_id, action_title,
            )
        except Exception as exc:
            logger.warning(
                "WritebackService: task creation failed | customer=%s title=%s error=%s",
                customer_id, action_title, exc,
            )
        return None

    async def find_similar_open_task(self, duplicate_key: str) -> Optional[dict]:
        """
        Check whether an open task with the same duplicate_key already exists.
        Returns the task dict if found, None otherwise.
        """
        if not self.sheets:
            return None
        try:
            loop = asyncio.get_event_loop()
            all_tasks = await asyncio.wait_for(
                loop.run_in_executor(None, self.sheets.list_all_open_tasks),
                timeout=_WRITE_TIMEOUT_SECONDS,
            )
            for task in all_tasks:
                if str(task.get("duplicate_key", "")).strip() == duplicate_key:
                    return task
        except Exception as exc:
            logger.warning(
                "WritebackService: duplicate check failed | key=%s error=%s",
                duplicate_key, exc,
            )
        return None

    async def log_client_response(
        self,
        customer_id: str,
        client_response: str,
        ticker: Optional[str] = None,
        notes: str = "",
    ) -> bool:
        """
        Log a client response (interested / neutral / declined).
        Creates a new interaction row — RM uses /log_response after a client call.
        """
        full_summary = f"Client response logged: {client_response}."
        if notes:
            full_summary += f" {notes}"
        if ticker:
            full_summary += f" Ticker discussed: {ticker}."

        interaction_id = await self.append_interaction_log(
            customer_id=customer_id,
            command="log-response",
            response_summary=full_summary,
            discussion_tickers=ticker or "",
            client_response=client_response,
            follow_up_required="No",
            interaction_type="Client Response Log",
            summary=full_summary,
        )
        return interaction_id is not None

    # ------------------------------------------------------------------
    # Private synchronous write methods (executed in thread pool)
    # ------------------------------------------------------------------

    def _sync_write_interaction(
        self,
        customer_id: str,
        command: str,
        response_summary: str,
        discussion_tickers: str,
        recommendation_given: str,
        client_response: str,
        follow_up_required: str,
        follow_up_due: str,
        interaction_type: Optional[str],
        summary: Optional[str],
    ) -> str:
        today = datetime.date.today().isoformat()
        interaction_id = f"I{uuid.uuid4().hex[:8].upper()}"

        row = {
            # V2 original columns
            "interaction_id": interaction_id,
            "customer_id": customer_id,
            "interaction_date": today,
            "channel": "Bot",
            "interaction_type": (
                interaction_type or _COMMAND_TYPE_MAP.get(command, command)
            ),
            "summary": summary or f"RM ran {command} via Aureus bot",
            "key_topics": "",
            "sentiment": "",
            "concern_level": "",
            "requested_action": "",
            "agent_response_summary": response_summary[:300],
            "follow_up_required": follow_up_required,
            "follow_up_due": follow_up_due,
            "owner": "RM",
            "last_updated": today,
            # V5.1 columns
            "discussion_tickers": discussion_tickers,
            "discussion_themes": "",
            "recommendation_given": recommendation_given,
            "recommendation_status": "Pending" if recommendation_given else "",
            "client_response": client_response,
            "meeting_required": "No",
            "meeting_date": "",
            "created_by": "Bot",
        }

        self.sheets.append_interaction(row)
        logger.info(
            "WritebackService: interaction logged | id=%s customer=%s command=%s",
            interaction_id, customer_id, command,
        )
        return interaction_id

    def _sync_write_task(
        self,
        customer_id: str,
        action_title: str,
        task_type: str,
        duplicate_key: str,
        linked_ticker: Optional[str],
        action_detail: str,
        rationale: str,
        urgency: str,
        due_date: str,
    ) -> str:
        today = datetime.date.today().isoformat()
        task_id = f"T{uuid.uuid4().hex[:8].upper()}"

        if not due_date:
            due_date = (
                datetime.date.today() + datetime.timedelta(days=7)
            ).isoformat()

        # task_category is the second segment of the duplicate_key
        task_category = duplicate_key.split(":")[1] if ":" in duplicate_key else ""

        row = {
            # V2 original columns
            "task_id": task_id,
            "customer_id": customer_id,
            "created_date": today,
            "task_type": task_type,
            "action_title": action_title,
            "action_detail": action_detail,
            "rationale": rationale,
            "urgency": urgency,
            "status": "Open",
            "due_date": due_date,
            "owner": "RM",
            "source": "Bot",
            "compliance_note": "",
            "completed_date": "",
            "outcome_note": "",
            # V5.1 columns
            "linked_interaction_id": "",
            "linked_ticker": linked_ticker or "",
            "task_category": task_category,
            "duplicate_key": duplicate_key,
            "priority_score": "",
        }

        self.sheets.append_task(row)
        logger.info(
            "WritebackService: task created | id=%s customer=%s title=%s key=%s",
            task_id, customer_id, action_title, duplicate_key,
        )
        return task_id


# ---------------------------------------------------------------------------
# Utility (importable by other modules)
# ---------------------------------------------------------------------------

def build_duplicate_key(
    customer_id: str,
    task_category: str,
    linked_ticker: Optional[str],
    intent_family: str,
) -> str:
    """
    Build the deduplication key for a task.
    Format: {customer_id}:{task_category}:{linked_ticker_or_none}:{intent_family}

    Examples:
      CUST001:followup:NVDA:idea_generation
      CUST001:review:none:meeting_pack
    """
    ticker_part = linked_ticker.upper().strip() if linked_ticker else "none"
    category = task_category.lower().strip().replace(" ", "_").replace("-", "_")
    family = intent_family.lower().strip().replace(" ", "_").replace("-", "_")
    return f"{customer_id}:{category}:{ticker_part}:{family}"
