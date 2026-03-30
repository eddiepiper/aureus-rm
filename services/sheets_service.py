"""
services/sheets_service.py

Google Sheets data access layer for Aureus RM.

Assumes a workbook with 5 tabs:
  - Customers
  - Holdings
  - Interactions
  - Watchlist
  - Tasks_NBA

The first row of each tab is a header row.
customer_id is the join key across all tabs.

If credentials are unavailable, the service raises SheetsUnavailableError
and the caller should fall back to mock data.
"""

import logging
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

TAB_CUSTOMERS = "Customers"
TAB_HOLDINGS = "Holdings"
TAB_INTERACTIONS = "Interactions"
TAB_WATCHLIST = "Watchlist"
TAB_TASKS = "Tasks_NBA"


class SheetsUnavailableError(Exception):
    """Raised when Google Sheets cannot be reached or credentials are invalid."""
    pass


class SheetsService:
    """
    Abstracts all Google Sheets read/write operations.

    Usage:
        svc = SheetsService(credentials_path, spreadsheet_id)
        svc.connect()
        customer = svc.get_customer_by_name("John Tan")
    """

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._spreadsheet = None
        self._cache: dict = {}

    def connect(self) -> None:
        """Authenticate and open the spreadsheet. Call once at startup."""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            client = gspread.authorize(creds)
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)
            logger.info("Connected to Google Sheets: %s", self.spreadsheet_id)
        except FileNotFoundError:
            raise SheetsUnavailableError(
                f"Service account credentials not found at: {self.credentials_path}\n"
                "Place your service-account.json in the credentials/ folder."
            )
        except Exception as e:
            raise SheetsUnavailableError(f"Failed to connect to Google Sheets: {e}")

    def _get_tab(self, tab_name: str) -> list[dict]:
        """Fetch all rows from a tab as a list of dicts. Caches per session."""
        if tab_name in self._cache:
            return self._cache[tab_name]
        try:
            ws = self._spreadsheet.worksheet(tab_name)
            rows = ws.get_all_records()
            self._cache[tab_name] = rows
            return rows
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Tab not found: %s", tab_name)
            return []
        except Exception as e:
            logger.error("Error reading tab %s: %s", tab_name, e)
            return []

    def invalidate_cache(self) -> None:
        """Clear the in-memory cache. Call if data may have changed."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def get_customer_by_name(self, name: str) -> Optional[dict]:
        """
        Find a customer by full_name (case-insensitive, partial match).
        Returns the first match or None.
        """
        rows = self._get_tab(TAB_CUSTOMERS)
        name_lower = name.lower().strip()
        for row in rows:
            full_name = str(row.get("full_name", "")).lower()
            preferred = str(row.get("preferred_name", "")).lower()
            if name_lower in full_name or name_lower in preferred:
                return row
        return None

    def get_customer_by_telegram_chat_id(self, chat_id: str) -> Optional[dict]:
        """Find a customer by their Telegram chat ID."""
        rows = self._get_tab(TAB_CUSTOMERS)
        for row in rows:
            if str(row.get("telegram_chat_id", "")).strip() == str(chat_id).strip():
                return row
        return None

    def validate_telegram_access(self, chat_id: str) -> bool:
        """Return True if chat_id is registered in the Customers tab."""
        return self.get_customer_by_telegram_chat_id(chat_id) is not None

    def get_customer_by_id(self, customer_id: str) -> Optional[dict]:
        """Find a customer by customer_id."""
        rows = self._get_tab(TAB_CUSTOMERS)
        for row in rows:
            if str(row.get("customer_id", "")).strip() == customer_id.strip():
                return row
        return None

    # ------------------------------------------------------------------
    # Holdings
    # ------------------------------------------------------------------

    def list_customer_holdings(self, customer_id: str) -> list[dict]:
        """Return all holdings for a customer_id."""
        rows = self._get_tab(TAB_HOLDINGS)
        return [r for r in rows if str(r.get("customer_id", "")) == customer_id]

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def list_customer_interactions(
        self, customer_id: str, limit: int = 5
    ) -> list[dict]:
        """Return the most recent N interactions for a customer, sorted by date desc."""
        rows = self._get_tab(TAB_INTERACTIONS)
        filtered = [r for r in rows if str(r.get("customer_id", "")) == customer_id]
        # Sort by interaction_date descending (ISO date strings sort correctly)
        filtered.sort(key=lambda r: r.get("interaction_date", ""), reverse=True)
        return filtered[:limit]

    # ------------------------------------------------------------------
    # Watchlist
    # ------------------------------------------------------------------

    def list_customer_watchlist(self, customer_id: str) -> list[dict]:
        """Return watchlist items for a customer."""
        rows = self._get_tab(TAB_WATCHLIST)
        return [r for r in rows if str(r.get("customer_id", "")) == customer_id]

    # ------------------------------------------------------------------
    # Tasks / Next Best Actions
    # ------------------------------------------------------------------

    def list_open_tasks(self, customer_id: str) -> list[dict]:
        """Return open tasks for a customer."""
        rows = self._get_tab(TAB_TASKS)
        return [
            r for r in rows
            if str(r.get("customer_id", "")) == customer_id
            and str(r.get("status", "")).lower() in ("open", "in progress", "pending")
        ]

    # Column order must match bootstrap_google_sheet.py TABS schema exactly
    INTERACTION_COLS = [
        "interaction_id", "customer_id", "interaction_date", "channel",
        "interaction_type", "summary", "key_topics", "sentiment",
        "concern_level", "requested_action", "agent_response_summary",
        "follow_up_required", "follow_up_due", "owner", "last_updated",
    ]
    TASK_COLS = [
        "task_id", "customer_id", "created_date", "task_type", "action_title",
        "action_detail", "rationale", "urgency", "status", "due_date",
        "owner", "source", "compliance_note", "completed_date", "outcome_note",
    ]

    def append_interaction(self, row: dict) -> None:
        """Append a new interaction row to the Interactions tab (column-ordered)."""
        try:
            ws = self._spreadsheet.worksheet(TAB_INTERACTIONS)
            ordered = [row.get(col, "") for col in self.INTERACTION_COLS]
            ws.append_row(ordered)
            self.invalidate_cache()
            logger.info("Appended interaction for customer: %s", row.get("customer_id"))
        except Exception as e:
            logger.error("Failed to append interaction: %s", e)
            raise

    def append_task(self, row: dict) -> None:
        """Append a new task row to the Tasks_NBA tab (column-ordered)."""
        try:
            ws = self._spreadsheet.worksheet(TAB_TASKS)
            ordered = [row.get(col, "") for col in self.TASK_COLS]
            ws.append_row(ordered)
            self.invalidate_cache()
            logger.info("Appended task for customer: %s", row.get("customer_id"))
        except Exception as e:
            logger.error("Failed to append task: %s", e)
            raise
