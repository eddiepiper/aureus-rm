"""
services/sheets_service.py

Google Sheets data access layer for Aureus RM.

Assumes a workbook with these tabs:
  - Customers
  - Holdings
  - Interactions
  - Watchlist
  - Tasks_NBA
  - AI_Assessment  (V7 — created by bootstrap_v7_ai_fields.py)

The first row of each tab is a header row.
customer_id is the join key across all tabs.

If credentials are unavailable, the service raises SheetsUnavailableError
and the caller should fall back to mock data.
"""

import datetime
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
TAB_AI_ASSESSMENT = "AI_Assessment"


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

    # ------------------------------------------------------------------
    # V5.1 — Book-wide queries (needed for attention list / morning brief)
    # ------------------------------------------------------------------

    def list_all_customers(self) -> list[dict]:
        """Return all customer records."""
        return list(self._get_tab(TAB_CUSTOMERS))

    def list_all_open_tasks(self) -> list[dict]:
        """Return all open tasks across the entire book."""
        rows = self._get_tab(TAB_TASKS)
        return [
            r for r in rows
            if str(r.get("status", "")).lower() in ("open", "in progress", "pending")
        ]

    def list_all_interactions(self, limit_days: int = 90) -> list[dict]:
        """Return all interactions within the last N days across all customers."""
        cutoff = (
            datetime.date.today() - datetime.timedelta(days=limit_days)
        ).isoformat()
        rows = self._get_tab(TAB_INTERACTIONS)
        return [r for r in rows if str(r.get("interaction_date", "")) >= cutoff]

    # Column order must match bootstrap_google_sheet.py TABS schema exactly.
    # V5.1 fields are appended to preserve backward compatibility.
    INTERACTION_COLS = [
        # V2 original (15 columns)
        "interaction_id", "customer_id", "interaction_date", "channel",
        "interaction_type", "summary", "key_topics", "sentiment",
        "concern_level", "requested_action", "agent_response_summary",
        "follow_up_required", "follow_up_due", "owner", "last_updated",
        # V5.1 additions (8 columns — appended)
        "discussion_tickers", "discussion_themes", "recommendation_given",
        "recommendation_status", "client_response", "meeting_required",
        "meeting_date", "created_by",
    ]
    TASK_COLS = [
        # V2 original (15 columns)
        "task_id", "customer_id", "created_date", "task_type", "action_title",
        "action_detail", "rationale", "urgency", "status", "due_date",
        "owner", "source", "compliance_note", "completed_date", "outcome_note",
        # V5.1 additions (5 columns — appended)
        "linked_interaction_id", "linked_ticker", "task_category",
        "duplicate_key", "priority_score",
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

    # ------------------------------------------------------------------
    # V7 — AI Assessment
    # ------------------------------------------------------------------

    # Column order must match bootstrap_v7_ai_fields.py AI_ASSESSMENT_HEADERS exactly.
    # Fields marked [DEPRECATED] are kept for backward-read compatibility but
    # are not written by the new engine. Remove them in a future schema migration.
    AI_ASSESSMENT_COLS = [
        # Customer identifiers
        "assessment_id", "customer_id", "customer_name",
        # Assessment metadata
        "assessment_date", "selected_criterion", "data_source", "source_is_internal",
        # Evidence
        "evidence_type", "evidence_date",
        # Income fields
        "annual_income", "income_currency", "income_period_start", "income_period_end",
        "income_source", "employer_name", "job_title",
        "salary_ytd", "bonus_ytd", "latest_noa_year", "latest_noa_amount",
        # DEPRECATED income field kept for backward read
        "income_year",                          # [DEPRECATED] replaced by income_period_start/end
        # Net personal assets fields
        "primary_residence_fmv", "primary_residence_secured_loan", "ownership_share_pct",
        "property_valuation_date",
        "other_personal_assets_value", "other_real_estate_value", "other_real_estate_secured_loans",
        "financial_assets_for_npa_value", "insurance_surrender_value",
        "business_interest_value", "other_personal_liabilities_value",
        "valuation_date", "statement_date",
        # DEPRECATED net assets fields kept for backward read
        "total_assets", "total_liabilities", "net_assets",   # [DEPRECATED] use explicit NPA fields
        "property_value",                                      # [DEPRECATED] use primary_residence_fmv
        "mortgage_liability",                                  # [DEPRECATED] use primary_residence_secured_loan
        "financial_assets_networth",                           # [DEPRECATED] use financial_assets_for_npa_value
        # Financial assets fields
        "total_financial_assets", "cash_holdings", "investment_holdings",
        "cpf_investment_amount", "funds_under_management_value",
        "financial_assets_related_liabilities",
        "margin_loan_balance", "portfolio_credit_line_balance",
        # FX
        "fx_rate_used", "fx_rate_date",
        # Joint account
        "joint_account_flag", "joint_account_note",
        # Decision output (written after assessment runs)
        "recognised_amount_sgd", "threshold_sgd", "pass_result",
        "confidence_level", "assessment_status",
        "missing_fields", "inconsistency_flags",
        "manual_review_required", "manual_review_reasons",
        # Checker workflow
        "checker_status", "memo_text", "assessor_notes",
        # DEPRECATED metadata field
        "ai_selected_criteria",                 # [DEPRECATED] use selected_criterion
        "last_updated",
    ]

    def list_customer_ai_assessments(self, customer_id: str) -> list[dict]:
        """Return all AI assessment rows for a customer_id."""
        rows = self._get_tab(TAB_AI_ASSESSMENT)
        return [r for r in rows if str(r.get("customer_id", "")) == customer_id]

    def append_ai_assessment(self, row: dict) -> None:
        """Append a new AI assessment row to the AI_Assessment tab (column-ordered)."""
        try:
            ws = self._spreadsheet.worksheet(TAB_AI_ASSESSMENT)
            ordered = [row.get(col, "") for col in self.AI_ASSESSMENT_COLS]
            ws.append_row(ordered)
            self.invalidate_cache()
            logger.info("Appended AI assessment for customer: %s", row.get("customer_id"))
        except Exception as e:
            logger.error("Failed to append AI assessment: %s", e)
            raise
