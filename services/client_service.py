"""
services/client_service.py

Orchestrates client data retrieval from SheetsService.
Assembles structured context objects used by command_router.py.

Falls back to mock data when SheetsService is unavailable.
"""

import logging
from typing import Optional

from services.sheets_service import SheetsService, SheetsUnavailableError
from services import mock_data  # noqa: F401 — used for mock fallbacks

logger = logging.getLogger(__name__)


class ClientNotFoundError(Exception):
    pass


class ClientService:
    def __init__(self, sheets: Optional[SheetsService], use_mock: bool = False):
        self.sheets = sheets
        self.use_mock = use_mock

    def _resolve_customer(self, name: str) -> dict:
        """Look up customer by name. Raises ClientNotFoundError if not found."""
        if self.use_mock or self.sheets is None:
            logger.warning("Using mock data for customer: %s", name)
            return mock_data.MOCK_CUSTOMER

        customer = self.sheets.get_customer_by_name(name)
        if not customer:
            raise ClientNotFoundError(
                f"No customer found matching '{name}'. "
                "Check the name or ensure the Customers tab is populated."
            )
        return customer

    def _get_holdings(self, customer_id: str) -> list[dict]:
        if self.use_mock or self.sheets is None:
            return mock_data.MOCK_HOLDINGS
        return self.sheets.list_customer_holdings(customer_id)

    def _get_interactions(self, customer_id: str, limit: int = 5) -> list[dict]:
        if self.use_mock or self.sheets is None:
            return mock_data.MOCK_INTERACTIONS
        return self.sheets.list_customer_interactions(customer_id, limit=limit)

    def _get_watchlist(self, customer_id: str) -> list[dict]:
        if self.use_mock or self.sheets is None:
            return mock_data.MOCK_WATCHLIST
        return self.sheets.list_customer_watchlist(customer_id)

    def _get_tasks(self, customer_id: str) -> list[dict]:
        if self.use_mock or self.sheets is None:
            return mock_data.MOCK_TASKS
        return self.sheets.list_open_tasks(customer_id)

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def build_client_review_context(self, client_name: str) -> dict:
        """
        Assemble full context for /client-review command.
        Returns: customer, holdings, interactions (last 5), open tasks
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "holdings": self._get_holdings(cid),
            "interactions": self._get_interactions(cid, limit=5),
            "tasks": self._get_tasks(cid),
            "is_mock": self.use_mock or self.sheets is None,
        }

    def build_portfolio_fit_context(self, client_name: str, ticker: str) -> dict:
        """
        Assemble context for /portfolio-fit command.
        Returns: customer, holdings, suitability snapshot, ticker requested
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "holdings": self._get_holdings(cid),
            "ticker": ticker.upper(),
            "is_mock": self.use_mock or self.sheets is None,
        }

    def build_meeting_pack_context(self, client_name: str) -> dict:
        """
        Assemble context for /meeting-pack command.
        Returns: customer, holdings, interactions, watchlist, open tasks
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "holdings": self._get_holdings(cid),
            "interactions": self._get_interactions(cid, limit=5),
            "watchlist": self._get_watchlist(cid),
            "tasks": self._get_tasks(cid),
            "is_mock": self.use_mock or self.sheets is None,
        }

    def build_next_best_action_context(self, client_name: str) -> dict:
        """
        Assemble context for /next-best-action command.
        Returns: customer, holdings, open tasks, recent interactions
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "holdings": self._get_holdings(cid),
            "tasks": self._get_tasks(cid),
            "interactions": self._get_interactions(cid, limit=3),
            "is_mock": self.use_mock or self.sheets is None,
        }

    # ------------------------------------------------------------------
    # V5.1 — New context builders
    # ------------------------------------------------------------------

    def build_relationship_status_context(self, client_name: str) -> dict:
        """
        Assemble context for /relationship-status command.
        Returns: customer, holdings (compressed), interactions (last 5), open tasks
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "holdings": self._get_holdings(cid),
            "interactions": self._get_interactions(cid, limit=5),
            "tasks": self._get_tasks(cid),
            "is_mock": self.use_mock or self.sheets is None,
        }

    def build_overdue_followups_context(self, client_name: str) -> dict:
        """
        Assemble context for /overdue-followups command.
        Returns: customer, tasks, recent interactions
        """
        customer = self._resolve_customer(client_name)
        cid = customer["customer_id"]
        return {
            "customer": customer,
            "tasks": self._get_tasks(cid),
            "interactions": self._get_interactions(cid, limit=3),
            "is_mock": self.use_mock or self.sheets is None,
        }

    def build_all_customers_context(self) -> list[dict]:
        """
        Return a minimal context list for all customers.
        Used by /attention-list and /morning-rm-brief.
        Each entry contains only the customer record (relationship and portfolio
        contexts are enriched separately by CommandRouter / RelationshipMemoryService).
        """
        if self.use_mock or self.sheets is None:
            return [{"customer": mock_data.MOCK_CUSTOMER}]
        customers = self.sheets.list_all_customers()
        return [{"customer": c} for c in customers if c.get("customer_id")]

    def build_log_response_context(
        self,
        client_name: str,
        response_status: str,
        ticker: Optional[str] = None,
    ) -> dict:
        """
        Assemble context for /log-response command.
        No holdings or interactions needed — just customer ID and the response.
        """
        customer = self._resolve_customer(client_name)
        return {
            "customer": customer,
            "client_response": response_status,
            "ticker": ticker,
            "is_mock": self.use_mock or self.sheets is None,
        }
