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
from typing import Optional

from services.client_service import ClientService, ClientNotFoundError
from services.sheets_service import SheetsService
from services import response_formatter as fmt
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService

logger = logging.getLogger(__name__)


class CommandRouter:
    def __init__(
        self,
        client_service: ClientService,
        claude_service=None,
        sheets_service: Optional[SheetsService] = None,
        financial_analysis=None,
        equity_research=None,
        relationship_memory=None,
        writeback_service=None,
        nba_agent=None,
        ai_approval_agent=None,
        chat_router=None,
    ):
        self.client = client_service
        self.claude = claude_service
        self.sheets = sheets_service
        self.fa = financial_analysis
        self.er = equity_research
        self.relationship_memory = relationship_memory
        self.writeback = writeback_service
        self.nba_agent = nba_agent
        self.ai_approval_agent = ai_approval_agent
        self.chat_router = chat_router
        self._current_chat_id: str = ""

        if self.claude:
            logger.info("CommandRouter: Claude API enabled")
        else:
            logger.info("CommandRouter: no Claude API — using template responses")
        if self.fa:
            logger.info("CommandRouter: FinancialAnalysisService attached")
        if self.er:
            logger.info("CommandRouter: EquityResearchService attached")
        if self.relationship_memory:
            logger.info("CommandRouter: RelationshipMemoryService attached")
        if self.writeback:
            logger.info("CommandRouter: WritebackService attached")
        if self.nba_agent:
            logger.info("CommandRouter: NBAAgent attached")
        if self.ai_approval_agent:
            logger.info("CommandRouter: AIApprovalAgent attached")

    # ------------------------------------------------------------------
    # Main router
    # ------------------------------------------------------------------

    async def route(self, command: str, args: list, chat_id: str = "") -> str:
        self._current_chat_id = chat_id  # made available to handlers via self
        handlers = {
            # V2 — Client & Portfolio
            "client-review":    self._client_review,
            "portfolio-fit":    self._portfolio_fit,
            "meeting-pack":     self._meeting_pack,
            "next-best-action": self._next_best_action,
            # V3 — Equity Research Plugin
            "earnings-deep-dive":  self._earnings_deep_dive,
            "stock-catalyst":      self._stock_catalyst,
            "thesis-check":        self._thesis_check,
            "idea-generation":     self._idea_generation,
            "morning-note":        self._morning_note,
            # V3 — Wealth Management Plugin
            "portfolio-scenario":  self._portfolio_scenario,
            # V5.1 — Relationship Memory + NBA
            "relationship-status": self._relationship_status,
            "overdue-followups":   self._overdue_followups,
            "attention-list":      self._attention_list,
            "morning-rm-brief":    self._morning_rm_brief,
            "log-response":        self._log_response,
            # V7 — AI Approval Agent
            "ai-assessment":       self._ai_assessment,
        }
        handler = handlers.get(command)
        if handler is None:
            return (
                f"Unknown command: `/{command}`\n\n"
                "V2: /client\\_review · /portfolio\\_fit · /meeting\\_pack · /next\\_best\\_action\n"
                "V3 Equity: /earnings\\_deep\\_dive · /stock\\_catalyst · /thesis\\_check · "
                "/idea\\_generation · /morning\\_note\n"
                "V3 Wealth: /portfolio\\_scenario\n"
                "V5.1: /relationship\\_status · /overdue\\_followups · "
                "/attention\\_list · /morning\\_rm\\_brief · /log\\_response\n"
                "V7: /ai\\_assessment"
            )
        try:
            response = await handler(args)
            # Update session state after successful execution
            self._update_session(chat_id, command, args)
            return response
        except ClientNotFoundError as e:
            return f"❌ {e}"
        except Exception as e:
            logger.exception("Error in /%s: %s", command, e)
            return f"❌ Error running `/{command}`: {e}"

    def _update_session(self, chat_id: str, command: str, args: list) -> None:
        """Update RelationshipMemoryService session state after a successful command."""
        if not self.relationship_memory or not chat_id:
            return
        updates: dict = {"last_command": command}
        # Client commands — args are [first_name, last_name, ...]
        client_commands = {
            "client-review", "meeting-pack", "next-best-action",
            "portfolio-fit", "portfolio-scenario", "idea-generation",
            "relationship-status", "overdue-followups", "log-response",
            "ai-assessment",
        }
        if command in client_commands and args:
            # For portfolio-fit: last arg is ticker, rest is name
            if command == "portfolio-fit" and len(args) >= 2:
                client_name = " ".join(args[:-1])
                ticker = args[-1].upper()
                updates["last_ticker"] = ticker
            else:
                client_name = " ".join(args)
            updates["last_client_name"] = client_name
        # Ticker commands
        ticker_commands = {
            "earnings-deep-dive", "stock-catalyst", "thesis-check", "morning-note"
        }
        if command in ticker_commands and args:
            updates["last_ticker"] = args[0].upper()
        updates["last_intent"] = command
        try:
            self.relationship_memory.update_session_state(chat_id, **updates)
        except Exception as exc:
            logger.debug("Session state update failed (non-critical): %s", exc)

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
            "name": customer.get("full_name") or customer.get("preferred_name"),
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
            "deployment_style": customer.get("deployment_style") or None,
        }

        # Holdings: separate CASA (deployable_flag=Yes) from invested positions
        holdings = ctx.get("holdings", [])
        def _safe_float(v):
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0

        def _is_casa(h: dict) -> bool:
            return str(h.get("deployable_flag", "")).strip().lower() in ("yes", "y")

        casa_holdings = [h for h in holdings if _is_casa(h)]
        invested_holdings = [h for h in holdings if not _is_casa(h)]

        # Top 5 invested positions by weight — CASA excluded from investment analysis
        sorted_invested = sorted(
            invested_holdings, key=lambda h: _safe_float(h.get("portfolio_weight_pct")), reverse=True
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
            for h in sorted_invested[:5]
        ]

        # Sector and geography concentration — invested positions only
        sector_weights: dict[str, float] = {}
        geo_weights: dict[str, float] = {}
        for h in invested_holdings:
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

        # Deployable liquidity summary — only present if CASA rows exist
        liquidity = None
        if casa_holdings:
            total_pct = sum(_safe_float(h.get("portfolio_weight_pct")) for h in casa_holdings)
            liquidity = {
                "total_deployable_pct": round(total_pct, 1),
                "holdings": [
                    {
                        "ticker": h.get("ticker"),
                        "currency": h.get("currency"),
                        "market_value": h.get("market_value"),
                        "weight_pct": h.get("portfolio_weight_pct"),
                    }
                    for h in casa_holdings
                ],
            }

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

        if liquidity:
            compressed["liquidity"] = liquidity

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
        """Try Claude with (possibly compressed) context; fall back to template on failure.

        V2 client commands produce raw ClientService contexts (have a 'customer' key)
        and need compression before Claude. V3 equity/portfolio contexts are already
        in their final shape and must NOT be compressed — doing so would strip all data.
        """
        if "customer" in raw_ctx:
            ctx_for_claude = self._compress_context(raw_ctx)
        else:
            ctx_for_claude = raw_ctx

        if self.claude:
            try:
                return await self.claude.generate(command, ctx_for_claude)
            except Exception as e:
                logger.warning("Claude failed for %s, using template fallback: %s", command, e)

        # Template fallback uses raw ctx (formatter expects original shape)
        formatters = {
            # V2
            "client-review":    fmt.format_client_review,
            "portfolio-fit":    fmt.format_portfolio_fit,
            "meeting-pack":     fmt.format_meeting_pack,
            "next-best-action": fmt.format_next_best_action,
            # V3 Equity
            "earnings-deep-dive":  fmt.format_earnings_deep_dive,
            "stock-catalyst":      fmt.format_stock_catalyst,
            "thesis-check":        fmt.format_thesis_check,
            "idea-generation":     fmt.format_idea_generation,
            "morning-note":        fmt.format_morning_note,
            # V3 Wealth
            "portfolio-scenario":  fmt.format_portfolio_scenario,
        }
        return formatters[command](raw_ctx)

    # ------------------------------------------------------------------
    # Write-back helpers (delegate to WritebackService when available)
    # ------------------------------------------------------------------

    def _schedule_interaction_log(
        self,
        customer_id: str,
        command: str,
        response_summary: str,
        **kwargs,
    ) -> None:
        """Non-blocking interaction log via WritebackService."""
        if not self.writeback:
            return
        self.writeback.schedule_interaction_log(
            customer_id, command, response_summary, **kwargs
        )

    def _schedule_followup_task(
        self,
        customer_id: str,
        action_title: str,
        task_type: str,
        task_category: str,
        intent_family: str,
        **kwargs,
    ) -> None:
        """Non-blocking duplicate-aware task creation via WritebackService."""
        if not self.writeback:
            return
        self.writeback.schedule_task_creation(
            customer_id=customer_id,
            action_title=action_title,
            task_type=task_type,
            task_category=task_category,
            intent_family=intent_family,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Relationship memory enrichment helper
    # ------------------------------------------------------------------

    def _enrich_with_relationship_memory(
        self, compressed_ctx: dict, customer_id: str
    ) -> dict:
        """
        Inject relationship context into a compressed portfolio context.
        Returns the original ctx unchanged if RelationshipMemoryService is unavailable.
        """
        if not self.relationship_memory:
            return compressed_ctx
        try:
            relationship_ctx = self.relationship_memory.summarize_relationship_state(
                customer_id
            )
            return {**compressed_ctx, "relationship_context": relationship_ctx}
        except Exception as exc:
            logger.warning(
                "RelationshipMemory enrichment failed for %s: %s", customer_id, exc
            )
            return compressed_ctx

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _client_review(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/client_review [client name]`\nExample: `/client_review John Tan`"
        ctx = self.client.build_client_review_context(name)
        response = await self._generate("client-review", ctx)
        if not ctx.get("is_mock"):
            cid = ctx["customer"]["customer_id"]
            self._schedule_interaction_log(cid, "client-review", response)
        return response

    async def _portfolio_fit(self, args: list) -> str:
        if len(args) < 2:
            return (
                "Usage: `/portfolio_fit [client name] [ticker]`\n"
                "Example: `/portfolio_fit John Tan D05.SI`"
            )
        ticker = args[-1].upper()
        name = " ".join(args[:-1])
        ctx = self.client.build_portfolio_fit_context(name, ticker)
        return await self._generate("portfolio-fit", ctx)

    async def _meeting_pack(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/meeting_pack [client name]`\nExample: `/meeting_pack John Tan`"
        ctx = self.client.build_meeting_pack_context(name)
        # Enrich with relationship memory for prior discussion + open follow-ups
        if not ctx.get("is_mock"):
            cid = ctx["customer"]["customer_id"]
            compressed = self._compress_context(ctx)
            enriched = self._enrich_with_relationship_memory(compressed, cid)
            response = await self._generate("meeting-pack", enriched)
            self._schedule_interaction_log(cid, "meeting-pack", response)
        else:
            response = await self._generate("meeting-pack", ctx)
        return response

    async def _next_best_action(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/next_best_action [client name]`\nExample: `/next_best_action John Tan`"
        ctx = self.client.build_next_best_action_context(name)
        cid = ctx["customer"]["customer_id"]
        is_mock = ctx.get("is_mock", False)

        # Enrich with relationship context — NBA Agent uses this for scoring
        compressed = self._compress_context(ctx)
        enriched = self._enrich_with_relationship_memory(compressed, cid)

        response = await self._generate("next-best-action", enriched)

        if not is_mock:
            self._schedule_interaction_log(cid, "next-best-action", response)
            self._schedule_followup_task(
                customer_id=cid,
                action_title="Review and act on NBA recommendations",
                task_type="Review",
                task_category="review",
                intent_family="next_best_action",
                action_detail="RM reviewed Aureus next best action output",
                rationale="Auto-created after /next-best-action",
                urgency="Medium",
            )
        return response

    # ------------------------------------------------------------------
    # V3 — Equity Research Plugin handlers
    # ------------------------------------------------------------------

    async def _earnings_deep_dive(self, args: list) -> str:
        if not args:
            return "Usage: `/earnings_deep_dive [ticker]`\nExample: `/earnings_deep_dive NVDA`"
        ticker = args[0].upper()
        if not self.er:
            return "❌ EquityResearchService not available."
        ctx = self.er.build_earnings_context(ticker)
        return await self._generate("earnings-deep-dive", ctx)

    async def _stock_catalyst(self, args: list) -> str:
        if not args:
            return "Usage: `/stock_catalyst [ticker]`\nExample: `/stock_catalyst TSM`"
        ticker = args[0].upper()
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        ctx = self.fa.build_catalyst_context(ticker)
        return await self._generate("stock-catalyst", ctx)

    async def _thesis_check(self, args: list) -> str:
        if not args:
            return "Usage: `/thesis_check [ticker]`\nExample: `/thesis_check AAPL`"
        ticker = args[0].upper()
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        ctx = self.fa.build_thesis_context(ticker)
        return await self._generate("thesis-check", ctx)

    async def _idea_generation(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/idea_generation [client name]`\nExample: `/idea_generation John Tan`"
        if not self.er:
            return "❌ EquityResearchService not available."
        client_ctx = self.client.build_client_review_context(name)
        compressed = self._compress_context(client_ctx)
        ctx = self.er.build_idea_context(compressed)
        # Inject previously discussed topics so the agent avoids re-surfacing them
        cid = client_ctx["customer"]["customer_id"]
        if self.relationship_memory:
            try:
                prior_topics = self.relationship_memory.get_last_discussed_topics(cid)
                if prior_topics:
                    ctx["previously_discussed_topics"] = prior_topics
            except Exception as exc:
                logger.debug("Could not fetch prior topics for %s: %s", cid, exc)
        return await self._generate("idea-generation", ctx)

    async def _morning_note(self, args: list) -> str:
        if not args:
            return "Usage: `/morning_note [ticker or sector]`\nExample: `/morning_note DBS`"
        input_str = args[0].upper()
        if not self.er:
            return "❌ EquityResearchService not available."
        ctx = self.er.build_morning_note_context(input_str)
        return await self._generate("morning-note", ctx)

    # ------------------------------------------------------------------
    # V5.1 — Relationship Memory + NBA command handlers
    # ------------------------------------------------------------------

    async def _relationship_status(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return (
                "Usage: `/relationship_status [client name]`\n"
                "Example: `/relationship_status John Tan`"
            )
        ctx = self.client.build_relationship_status_context(name)
        cid = ctx["customer"]["customer_id"]
        compressed = self._compress_context(ctx)
        enriched = self._enrich_with_relationship_memory(compressed, cid)
        response = await self._generate("relationship-status", enriched)
        if not ctx.get("is_mock"):
            self._schedule_interaction_log(cid, "relationship-status", response)
        return response

    async def _overdue_followups(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return (
                "Usage: `/overdue_followups [client name]`\n"
                "Example: `/overdue_followups John Tan`"
            )
        ctx = self.client.build_overdue_followups_context(name)
        cid = ctx["customer"]["customer_id"]
        compressed = self._compress_context(ctx)
        enriched = self._enrich_with_relationship_memory(compressed, cid)
        return await self._generate("overdue-followups", enriched)

    def _build_customer_inputs(self, all_entries: list) -> list[dict]:
        """
        Enrich each customer entry with relationship context.
        Returns list of {customer, relationship_ctx, portfolio_ctx} dicts
        ready for NBAAgent.score_all_customers().
        """
        result = []
        for entry in all_entries:
            customer = entry.get("customer", {})
            cid = customer.get("customer_id", "")
            relationship_ctx = {}
            if self.relationship_memory and cid:
                try:
                    relationship_ctx = self.relationship_memory.summarize_relationship_state(cid)
                except Exception as exc:
                    logger.debug("Relationship context failed for %s: %s", cid, exc)
            result.append({
                "customer": customer,
                "relationship_ctx": relationship_ctx,
                "portfolio_ctx": {},
            })
        return result

    async def _attention_list(self, args: list) -> str:
        """
        Load all customers, score each with NBA Agent signals,
        and surface the top 5 requiring RM attention.
        """
        is_mock = self.client.use_mock or self.client.sheets is None
        all_entries = self.client.build_all_customers_context()
        customer_inputs = self._build_customer_inputs(all_entries)

        if self.nba_agent:
            scored_clients = self.nba_agent.score_all_customers(customer_inputs)
        else:
            scored_clients = customer_inputs

        ctx = {
            "scored_clients": scored_clients,
            "is_mock": is_mock,
        }
        return await self._generate("attention-list", ctx)

    async def _morning_rm_brief(self, args: list) -> str:
        """
        Load all customers, score each, and produce the RM's daily brief.
        """
        is_mock = self.client.use_mock or self.client.sheets is None
        all_entries = self.client.build_all_customers_context()
        customer_inputs = self._build_customer_inputs(all_entries)

        if self.nba_agent:
            scored_clients = self.nba_agent.score_all_customers(customer_inputs)
        else:
            scored_clients = customer_inputs

        ctx = {
            "scored_clients": scored_clients,
            "is_mock": is_mock,
        }
        return await self._generate("morning-rm-brief", ctx)

    async def _log_response(self, args: list) -> str:
        """
        Log a client response after a real-world interaction.
        Usage: /log_response [client name] [interested|neutral|declined] [optional ticker]

        Examples:
          /log_response John Tan interested NVDA
          /log_response Sarah Lim declined
        """
        VALID_STATUSES = {"interested", "neutral", "declined", "pending"}

        if len(args) < 2:
            return (
                "Usage: `/log_response [client name] [interested|neutral|declined] [optional ticker]`\n"
                "Example: `/log_response John Tan interested NVDA`"
            )

        # Parse: last arg may be a ticker, second-to-last is the status
        possible_status = args[-1].lower()
        possible_ticker = None

        if possible_status not in VALID_STATUSES and len(args) >= 3:
            # Last arg is a ticker, second-to-last is status
            possible_ticker = args[-1].upper()
            possible_status = args[-2].lower()
            name_args = args[:-2]
        elif possible_status in VALID_STATUSES:
            name_args = args[:-1]
        else:
            return (
                f"❌ Unrecognised response status: `{possible_status}`\n"
                "Use: `interested`, `neutral`, `declined`, or `pending`."
            )

        name = " ".join(name_args) if name_args else None
        if not name:
            return "❌ Please include the client name. Example: `/log_response John Tan interested NVDA`"

        try:
            ctx = self.client.build_log_response_context(
                name, possible_status, ticker=possible_ticker
            )
        except Exception as e:
            return f"❌ {e}"

        is_mock = ctx.get("is_mock", False)
        cid = ctx["customer"]["customer_id"]
        client_name = (
            ctx["customer"].get("full_name")
            or ctx["customer"].get("preferred_name")
            or name
        )

        if not is_mock and self.writeback:
            success = await self.writeback.log_client_response(
                customer_id=cid,
                client_response=possible_status.title(),
                ticker=possible_ticker,
            )
            if success:
                ticker_note = f" re: {possible_ticker}" if possible_ticker else ""
                return (
                    f"✅ Logged: *{client_name}* responded *{possible_status.title()}*"
                    f"{ticker_note}.\n\n"
                    "Relationship record updated.\n\n"
                    "_For internal RM use only. Not investment advice._"
                )
            else:
                return "❌ Failed to log client response. Check your Google Sheets connection."
        else:
            ticker_note = f" re: {possible_ticker}" if possible_ticker else ""
            return (
                f"⚠️ *MOCK MODE* — would log: *{client_name}* responded "
                f"*{possible_status.title()}*{ticker_note}.\n\n"
                "_For internal RM use only. Not investment advice._"
            )

    # ------------------------------------------------------------------
    # V3 — Wealth Management Plugin handler
    # ------------------------------------------------------------------

    async def _portfolio_scenario(self, args: list) -> str:
        name = " ".join(args) if args else None
        if not name:
            return "Usage: `/portfolio_scenario [client name]`\nExample: `/portfolio_scenario John Tan`"
        if not self.fa:
            return "❌ FinancialAnalysisService not available."
        client_ctx = self.client.build_client_review_context(name)
        compressed = self._compress_context(client_ctx)

        held_tickers = [h["ticker"] for h in compressed.get("top_holdings", []) if h.get("ticker")]
        scenarios_by_ticker = [
            {"ticker": t, **self.fa.build_scenario_context(t)}
            for t in held_tickers
        ]

        ctx = {
            "client_name": compressed.get("profile", {}).get("name", name),
            "is_mock": True,
            "data_freshness": "framework-based",
            "source_label": "MOCK / NOT REAL-TIME",
            "profile": compressed.get("profile", {}),
            "top_holdings": compressed.get("top_holdings", []),
            "scenarios_by_ticker": scenarios_by_ticker,
        }
        if compressed.get("liquidity"):
            ctx["liquidity"] = compressed["liquidity"]
        return await self._generate("portfolio-scenario", ctx)

    # ------------------------------------------------------------------
    # V7 — AI Approval Agent handler
    # ------------------------------------------------------------------

    async def _ai_assessment(self, args: list) -> str:
        """
        Run an Accredited Investor eligibility assessment for a client.

        Usage: /ai_assessment [client name] [optional: 1/2/3/income/net assets/financial assets]

        If no criteria is provided, Aureus asks the RM to specify one.
        The RM can reply with a number (1/2/3/4) or text (income / net assets / financial assets).
        """
        from services.ai_approval_agent import normalize_criteria

        chat_id = self._current_chat_id

        # ------------------------------------------------------------------
        # Parse args: [name words...] [optional criteria]
        # Try last arg, then last two args, for a criteria match.
        # ------------------------------------------------------------------
        criteria = None
        name_args = list(args)

        if name_args:
            normalized = normalize_criteria(name_args[-1].lower())
            if normalized:
                criteria = normalized
                name_args = name_args[:-1]

        if criteria is None and len(name_args) >= 2:
            two_word = " ".join(name_args[-2:]).lower()
            normalized = normalize_criteria(two_word)
            if normalized:
                criteria = normalized
                name_args = name_args[:-2]

        name = " ".join(name_args).strip()
        if not name:
            return (
                "Usage: `/ai_assessment [client name]`\n"
                "Example: `/ai_assessment John Tan`\n"
                "Or with criteria: `/ai_assessment John Tan 1`"
            )

        # ------------------------------------------------------------------
        # No criteria — ask the RM and set pending state in ChatRouter
        # so the next free-text reply is captured automatically.
        # ------------------------------------------------------------------
        if criteria is None:
            question = (
                f"Which eligibility basis should I assess for *{name.title()}*?\n\n"
                "1️⃣  Income ≥ SGD 300,000\n"
                "2️⃣  Net Personal Assets > SGD 2,000,000\n"
                "3️⃣  Net Financial Assets > SGD 1,000,000\n\n"
                "Reply with `1`, `2`, or `3`"
            )
            if self.chat_router and chat_id:
                state = self.chat_router._get_state(chat_id)
                state.intent = "ai_assessment"
                state.client_name = name.title()
                state.waiting_for = "criteria"
            return question

        # ------------------------------------------------------------------
        # Resolve client
        # ------------------------------------------------------------------
        ctx = self.client.build_client_review_context(name)
        customer = ctx.get("customer", {})
        cid = customer.get("customer_id", "")
        is_mock = ctx.get("is_mock", False)

        # ------------------------------------------------------------------
        # Load AI assessment data (Sheets → mock fallback)
        # ------------------------------------------------------------------
        ai_data = self._get_ai_assessment_data(cid, is_mock=is_mock)
        ctx["ai_assessment_data"] = ai_data
        ctx["criteria"] = criteria
        ctx["customer_name"] = (
            customer.get("preferred_name") or customer.get("full_name") or name.title()
        )

        # ------------------------------------------------------------------
        # Run deterministic assess() now so we have the result for writeback decisions.
        # generate() will call assess() again internally — that's intentional:
        # the deterministic layer is fast and the result drives memo generation.
        # ------------------------------------------------------------------
        has_missing = False
        has_issues = False
        if ai_data and self.ai_approval_agent and hasattr(self.ai_approval_agent, "assess"):
            prelim = self.ai_approval_agent.assess(
                ai_data,
                criterion=criteria,
                customer_name=ctx["customer_name"],
                customer_id=cid,
            )
            has_missing = bool(prelim.missing_fields)
            has_issues  = bool(prelim.inconsistency_flags) or prelim.manual_review_required

        response = await self._generate("ai-assessment", ctx)

        # ------------------------------------------------------------------
        # Writeback: always log the assessment as an interaction.
        # Create a follow-up task only if missing data exists.
        # ------------------------------------------------------------------
        if not is_mock and self.writeback and cid:
            self.writeback.schedule_interaction_log(
                customer_id=cid,
                command="ai-assessment",
                summary=f"AI assessment run | criterion={criteria} | missing_data={has_missing} | flags={has_issues}",
                response_text=response[:500],
            )
            if has_missing or has_issues:
                self.writeback.schedule_task_creation(
                    customer_id=cid,
                    task_category="ai_assessment",
                    action_title=f"Complete AI assessment data — {ctx['customer_name']}",
                    action_detail=(
                        "AI assessment flagged missing or inconsistent data. "
                        "RM to update AI_Assessment sheet before re-running."
                    ),
                    urgency="Medium",
                    source="AIApprovalAgent",
                )

        return response

    def _get_ai_assessment_data(self, customer_id: str, is_mock: bool = False) -> dict:
        """
        Load the most recent AI assessment record for a customer.
        Uses live Sheets if available, falls back to mock data.
        """
        if not is_mock and self.sheets and customer_id:
            try:
                rows = self.sheets.list_customer_ai_assessments(customer_id)
                if rows:
                    return sorted(
                        rows,
                        key=lambda r: str(r.get("last_updated", "")),
                        reverse=True,
                    )[0]
            except Exception as exc:
                logger.warning("Failed to load AI assessment from Sheets: %s", exc)

        # Mock fallback
        from services import mock_data
        for row in getattr(mock_data, "MOCK_AI_ASSESSMENTS", []):
            if str(row.get("customer_id", "")) == customer_id:
                return row
        return {}
