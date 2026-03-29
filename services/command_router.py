"""
services/command_router.py

Routes Telegram commands to the appropriate service methods and returns
formatted text for Telegram delivery.

Response generation priority:
  1. ClaudeService (LLM-generated) — if ANTHROPIC_API_KEY is set
  2. response_formatter (template-based) — fallback if Claude is unavailable

This means the bot works without an API key (using structured templates),
and upgrades to Claude-generated responses when the key is present.
"""

import logging
from typing import Optional

from services.client_service import ClientService, ClientNotFoundError
from services import response_formatter as fmt

logger = logging.getLogger(__name__)


class CommandRouter:
    def __init__(
        self,
        client_service: ClientService,
        claude_service=None,  # services.claude_service.ClaudeService | None
    ):
        self.client = client_service
        self.claude = claude_service

        if self.claude:
            logger.info("CommandRouter: Claude API enabled — using LLM responses")
        else:
            logger.info("CommandRouter: Claude API not configured — using template responses")

    async def route(self, command: str, args: list[str]) -> str:
        """
        Dispatch a command and return a formatted response string.

        Args:
            command: command name without leading slash (e.g. "client-review")
            args:    list of string arguments parsed from the Telegram message

        Returns:
            Formatted markdown string for Telegram.
        """
        handlers = {
            "client-review": self._client_review,
            "portfolio-fit": self._portfolio_fit,
            "meeting-pack": self._meeting_pack,
            "next-best-action": self._next_best_action,
        }

        handler = handlers.get(command)
        if handler is None:
            return (
                f"Unknown command: `/{command}`\n\n"
                "Available commands:\n"
                "- /client\\_review \\[name\\]\n"
                "- /portfolio\\_fit \\[name\\] \\[ticker\\]\n"
                "- /meeting\\_pack \\[name\\]\n"
                "- /next\\_best\\_action \\[name\\]"
            )

        try:
            return await handler(args)
        except ClientNotFoundError as e:
            return f"❌ {e}"
        except Exception as e:
            logger.exception("Unexpected error in command /%s: %s", command, e)
            return (
                f"❌ Error running `/{command}`.\n"
                f"{e}\n\n"
                "Check your Google Sheets connection or try again."
            )

    # ------------------------------------------------------------------
    # Argument validation helpers
    # ------------------------------------------------------------------

    def _require_name(self, command: str, args: list[str]) -> Optional[str]:
        if not args:
            return None
        return " ".join(args)

    # ------------------------------------------------------------------
    # Response generation — Claude first, template fallback
    # ------------------------------------------------------------------

    async def _generate(self, command: str, ctx: dict) -> str:
        """Try Claude first (async); fall back to template formatter."""
        if self.claude:
            try:
                return await self.claude.generate(command, ctx)
            except Exception as e:
                logger.warning(
                    "Claude API failed for command=%s, falling back to template. Error: %s",
                    command, e,
                )
        # Template fallback
        formatters = {
            "client-review": fmt.format_client_review,
            "portfolio-fit": fmt.format_portfolio_fit,
            "meeting-pack": fmt.format_meeting_pack,
            "next-best-action": fmt.format_next_best_action,
        }
        return formatters[command](ctx)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _client_review(self, args: list[str]) -> str:
        client_name = self._require_name("client-review", args)
        if not client_name:
            return "Usage: `/client_review [client name]`\nExample: `/client_review John Tan`"
        ctx = self.client.build_client_review_context(client_name)
        return await self._generate("client-review", ctx)

    async def _portfolio_fit(self, args: list[str]) -> str:
        if len(args) < 2:
            return (
                "Usage: `/portfolio_fit [client name] [ticker]`\n"
                "Example: `/portfolio_fit John Tan D05.SI`\n\nTicker must be the last argument."
            )
        ticker = args[-1].upper()
        client_name = " ".join(args[:-1])
        ctx = self.client.build_portfolio_fit_context(client_name, ticker)
        return await self._generate("portfolio-fit", ctx)

    async def _meeting_pack(self, args: list[str]) -> str:
        client_name = self._require_name("meeting-pack", args)
        if not client_name:
            return "Usage: `/meeting_pack [client name]`\nExample: `/meeting_pack John Tan`"
        ctx = self.client.build_meeting_pack_context(client_name)
        return await self._generate("meeting-pack", ctx)

    async def _next_best_action(self, args: list[str]) -> str:
        client_name = self._require_name("next-best-action", args)
        if not client_name:
            return "Usage: `/next_best_action [client name]`\nExample: `/next_best_action John Tan`"
        ctx = self.client.build_next_best_action_context(client_name)
        return await self._generate("next-best-action", ctx)
