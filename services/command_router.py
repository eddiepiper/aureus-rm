"""
services/command_router.py

Routes Telegram commands to the appropriate service methods.

Response generation:
  1. ClaudeService (primary) — if ANTHROPIC_API_KEY is set
  2. response_formatter (fallback) — template-based, no API key required

Context is compressed before passing to Claude — raw Sheets data is distilled
into a signal-rich summary so Claude generates insight, not reports.
"""

import json
import logging
import datetime
import uuid
from typing import Optional

from services.client_service import ClientService, ClientNotFoundError
from services.sheets_service import SheetsService
from services import response_formatter as fmt

logger = logging.getLogger(__name__)


class CommandRouter:
    def __init__(
        self,
        client_service: ClientService,
        claude_service=None,
        sheets_service: Optional[SheetsService] = None,
    ):
        self.client = client_service
        self.claude = claude_service
        self.sheets = sheets_service

        if self.claude:
            logger.info("CommandRouter: Claude API enabled")
        else:
            logger.info("CommandRouter: no Claude API — using template responses")

    # ------------------------------------------------------------------
    # Main router
    # ------------------------------------------------------------------

    async def route(self, command: str, args: list[str]) -> str:
        handlers = {
            "client-review":    self._client_review,
            "portfolio-fit":    self._portfolio_fit,
            "meeting-pack":     self._meeting_pack,
            "next-best-action": self._next_best_action,
        }
        handler = handlers.get(command)
        if handler is None:
            return (
                f"Unknown command: `/{command}`\n\n"
                "Available: /client\\_review · /portfolio\\_fit · "
                "/meeting\\_pack · /next\\_best\\_action"
            )
        try:
            return await handler(args)
        except ClientNotFoundError as e:
            return f"❌ {e}"
        except Exception as e:
            logger.exception("Error in /%s: %s", command, e)
            return f"❌ Error running `/{command}`: {e}"

    # ------------------------------------------------------------------
    # Context compression — distil raw Sheets data for Claude
    # ------------------------------------------------------------------

    def _compress_context(self, ctx: dict) -> dict:
        """
        Convert raw ClientService context into a signal-rich summary.
        Removes noise (full interaction text, redundant fields) so Claude
        can focus on interpretation rather than transcription.
        """
        customer = ctx.get("customer", {})

        profile = {
            "name": customer.get("preferred_name") or customer.get("full_name"),
            "segment": customer.get("segment"),
            "risk_profile": customer.get("risk_profile"),
            "objective": customer.get("investment_objective"),
            "horizon": customer.get("investment_horizon"),
            "preferred_markets": customer.get("preferred_markets"),
            "restricted_markets": customer.get("restricted_markets") or None,
            "esg_preference": customer.get("esg_preference"),
            "dividend_preference": customer.get("dividend_preference"),
            "last_review_date": customer.get("last_review_date"),
            "next_review_due": customer.get("next_review_due"),
            "notes": customer.get("notes_summary") or None,
        }

        # Holdings: top 5 by weight, key metrics only
        holdings = ctx.get("holdings", [])
        def _safe_float(v):
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0

        sorted_holdings = sorted(
            holdings, key=lambda h: _safe_float(h.get("portfolio_weight_pct")), reverse=True
        )
        top_holdings = [
            {
                "ticker": h.get("ticker"),
                "name": h.get("security_name"),
                "weight_pct": h.get("portfolio_weight_pct"),
                "unrealized_pnl_pct": h.get("unrealized_pnl_pct"),
                "sector": h.get("sector"),
                "geography": h.get("geography"),
                "conviction": h.get("conviction_level"),
            }
            for h in sorted_holdings[:5]
        ]

        # Sector and geography concentration
        sector_weights: dict[str, float] = {}
        geo_weights: dict[str, float] = {}
        for h in holdings:
            sector_weights[h.get("sector", "Other")] = (
                sector_weights.get(h.get("sector", "Other"), 0) + _safe_float(h.get("portfolio_weight_pct"))
            )
            geo_weights[h.get("geography", "Other")] = (
                geo_weights.get(h.get("geography", "Other"), 0) + _safe_float(h.get("portfolio_weight_pct"))
            )

        concentration = {}
        if sector_weights:
            top_s = max(sector_weights.items(), key=lambda x: x[1])
            concentration["top_sector"] = f"{top_s[0]} {top_s[1]:.0f}%"
        if geo_weights:
            top_g = max(geo_weights.items(), key=lambda x: x[1])
            concentration["top_geography"] = f"{top_g[0]} {top_g[1]:.0f}%"

        # Interactions: last 3, distilled
        interactions = ctx.get("interactions", [])
        recent = [
            {
                "date": i.get("interaction_date"),
                "type": i.get("interaction_type"),
                "topics": i.get("key_topics"),
                "follow_up_required": i.get("follow_up_required"),
                "follow_up_due": i.get("follow_up_due") or None,
            }
            for i in interactions[:3]
        ]

        # Tasks: title + urgency + due only
        open_tasks = [
            {
                "title": t.get("action_title"),
                "urgency": t.get("urgency"),
                "due": t.get("due_date") or None,
            }
            for t in ctx.get("tasks", [])
        ]

        compressed = {
            "profile": profile,
            "top_holdings": top_holdings,
            "concentration": concentration,
            "recent_interactions": recent,
            "open_tasks": open_tasks,
            "is_mock": ctx.get("is_mock", False),
        }

        if "ticker" in ctx:
            compressed["ticker_requested"] = ctx["ticker"]

        if "watchlist" in ctx:
            compressed["watchlist"] = [
                {
                    "ticker": w.get("ticker"),
                    "name": w.get("security_name"),
                    "reason": w.get("reason_for_interest"),
                    "priority": w.get("priority"),
                }
                for w in ctx.get("watchlist", [])
            ]

        return compressed

    # ------------------------------------------------------------------
    # Response generation — Claude primary, template fallback
    # ------------------------------------------------------------------

    async def _generate(self, command: str, raw_ctx: dict) -> str:
        """Compress context, then try Claude; fall back to template on failure."""
        compressed = self._compress_context(raw_ctx)

        if self.claude:
            try:
                return await self.claude.generate(command, compressed)
            except Exception as e:
                logger.warning("Claude failed for %s, using template fallback: %s", command, e)

        # Template fallback uses raw ctx (formatter expects original shape)
        formatters = {
            "client-review":    fmt.format_client_review,
            "portfolio-fit":    fmt.format_portfolio_fit,
            "meeting-pack":     fmt.format_meeting_pack,
            "next-best-action": fmt.format_next_best_action,
        }
        return formatters[command](raw_ctx)

    # ------------------------------------------------------------------
    # Write-back helpers
    # ------------------------------------------------------------------

    def _write_interaction(self, customer_id: str, interaction_type: str, response_summary: str) -> None:
        if not self.sheets:
            return
        today = datetime.date.today().isoformat()
        row = {
            "interaction_id": f"I{uuid.uuid4().hex[:8].upper()}",
            "customer_id": customer_id,
            "interaction_date": today,
            "channel": "Bot",
            "interaction_type": interaction_type,
            "summary": f"RM ran {interaction_type} via Aureus bot",
            "key_topics": "",
            "sentiment": "",
            "concern_level": "",
            "requested_action": "",
            "agent_response_summary": response_summary[:300],
            "follow_up_required": "No",
            "follow_up_due": "",
            "owner": "RM",
            "last_updated": today,
        }
        try:
            self.sheets.append_interaction(row)
        except Exception as e:
            logger.warning("Write-back failed (interaction): %s", e)

    def _write_nba_task(self, customer_id: str) -> None:
        if not self.sheets:
            return
        today = datetime.date.today().isoformat()
        row = {
            "task_id": f"T{uuid.uuid4().hex[:8].upper()}",
            "customer_id": customer_id,
            "created_date": today,
            "task_type": "Review",
            "action_title": "Review NBA recommendations",
            "action_detail": "RM reviewed next best actions generated by Aureus bot",
            "rationale": "Auto-generated by Aureus bot",
            "urgency": "Medium",
            "status": "Open",
            "due_date": "",
            "owner": "RM",
            "source": "Bot",
            "compliance_note": "",
            "completed_date": "",
            "outcome_note": "",
        }
        try:
            self.sheets.append_task(row)
        except Exception as e:
            logger.warning("Write-back failed (task): %s", e)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _client_review(self, args: list[str]) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/client_review [client name]`\nExample: `/client_review John Tan`"
        ctx = self.client.build_client_review_context(name)
        response = await self._generate("client-review", ctx)
        if not ctx.get("is_mock"):
            self._write_interaction(ctx["customer"]["customer_id"], "Client Review", response)
        return response

    async def _portfolio_fit(self, args: list[str]) -> str:
        if len(args) < 2:
            return (
                "Usage: `/portfolio_fit [client name] [ticker]`\n"
                "Example: `/portfolio_fit John Tan D05.SI`"
            )
        ticker = args[-1].upper()
        name = " ".join(args[:-1])
        ctx = self.client.build_portfolio_fit_context(name, ticker)
        return await self._generate("portfolio-fit", ctx)

    async def _meeting_pack(self, args: list[str]) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/meeting_pack [client name]`\nExample: `/meeting_pack John Tan`"
        ctx = self.client.build_meeting_pack_context(name)
        response = await self._generate("meeting-pack", ctx)
        if not ctx.get("is_mock"):
            self._write_interaction(ctx["customer"]["customer_id"], "Meeting Pack", response)
        return response

    async def _next_best_action(self, args: list[str]) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/next_best_action [client name]`\nExample: `/next_best_action John Tan`"
        ctx = self.client.build_next_best_action_context(name)
        response = await self._generate("next-best-action", ctx)
        if not ctx.get("is_mock"):
            cid = ctx["customer"]["customer_id"]
            self._write_interaction(cid, "Next Best Action", response)
            self._write_nba_task(cid)
        return response
