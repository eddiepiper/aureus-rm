"""
bot/telegram_bot.py

Telegram bot interface for Aureus RM Copilot.
Handles incoming commands and delegates to command_router.

Supported commands:
  /start
  /client-review [name]
  /portfolio-fit [name] [ticker]
  /meeting-pack [name]
  /next-best-action [name]
  /help
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from services.command_router import CommandRouter
from services import chat_router
from services.sheets_service import SheetsService

logger = logging.getLogger(__name__)

HELP_TEXT = """
*Aureus RM Copilot — V3*

*V2 — Client & Portfolio*
/client\\_review [name] — Full client review
/portfolio\\_fit [name] [ticker] — Portfolio fit check
/meeting\\_pack [name] — Meeting prep pack
/next\\_best\\_action [name] — Suggested next actions

*V3 — Equity Research*
/earnings\\_deep\\_dive [ticker] — Earnings results deep dive
/stock\\_catalyst [ticker] — Near-term catalyst brief
/thesis\\_check [ticker] — Bull/bear thesis check
/idea\\_generation [name] — Mandate-aware stock ideas
/morning\\_note [ticker] — Morning briefing for a name

*V3 — Portfolio Intelligence*
/portfolio\\_scenario [name] — Portfolio scenario analysis

/help — show this message
"""


def build_application(
    token: str,
    router: CommandRouter,
    sheets_service: Optional[SheetsService] = None,
) -> Application:
    """
    Build and return the Telegram Application with all handlers registered.

    sheets_service: when provided, every non-/start handler validates the
    sender's Telegram chat_id against the Customers tab before proceeding.
    Pass None (or omit) to disable access control (mock / dev mode).
    """
    app = Application.builder().token(token).build()

    # Bind handlers
    app.add_handler(CommandHandler("start", _start_handler))
    app.add_handler(CommandHandler("help", _help_handler))
    app.add_handler(CommandHandler("client_review",    _make_command_handler("client-review",    router, sheets_service)))
    app.add_handler(CommandHandler("portfolio_fit",    _make_command_handler("portfolio-fit",    router, sheets_service)))
    app.add_handler(CommandHandler("meeting_pack",     _make_command_handler("meeting-pack",     router, sheets_service)))
    app.add_handler(CommandHandler("next_best_action", _make_command_handler("next-best-action", router, sheets_service)))
    # V3 — Equity Research Plugin
    app.add_handler(CommandHandler("earnings_deep_dive", _make_command_handler("earnings-deep-dive", router, sheets_service)))
    app.add_handler(CommandHandler("stock_catalyst",     _make_command_handler("stock-catalyst",     router, sheets_service)))
    app.add_handler(CommandHandler("thesis_check",       _make_command_handler("thesis-check",       router, sheets_service)))
    app.add_handler(CommandHandler("idea_generation",    _make_command_handler("idea-generation",    router, sheets_service)))
    app.add_handler(CommandHandler("morning_note",       _make_command_handler("morning-note",       router, sheets_service)))
    # V3 — Wealth Management Plugin
    app.add_handler(CommandHandler("portfolio_scenario", _make_command_handler("portfolio-scenario", router, sheets_service)))

    # Natural-language messages (non-command text)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _make_chat_handler(router, sheets_service))
    )

    return app


def _check_access(chat_id: str, sheets: Optional[SheetsService]) -> bool:
    """Return True if this chat_id is allowed. Always True when sheets is None (mock mode)."""
    if sheets is None:
        return True
    try:
        return sheets.validate_telegram_access(chat_id)
    except Exception:
        return True  # fail open on Sheets error to avoid locking out RMs


def _make_chat_handler(router: CommandRouter, sheets: Optional[SheetsService] = None):
    """
    Factory: returns an async handler for free-text (non-command) messages.
    Delegates to chat_router for intent detection and multi-turn state.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = str(update.effective_chat.id)
        text = update.message.text or ""

        if not _check_access(chat_id, sheets):
            await update.message.reply_text(
                "⛔ Access denied. Your Telegram ID is not registered.\n"
                "Contact your administrator to be added to the system.",
                parse_mode="Markdown",
            )
            return

        resolution = chat_router.resolve(chat_id, text)

        if resolution.ready:
            await update.message.reply_text("⏳ Fetching data...", parse_mode="Markdown")
            try:
                response = await router.route(resolution.command, resolution.args)
            except Exception as e:
                logger.exception("Error executing chat-resolved command: %s", e)
                response = f"❌ Something went wrong: {e}"
            for chunk in _split_message(response):
                await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(resolution.reply, parse_mode="Markdown")

    return handler


def _make_command_handler(command_name: str, router: CommandRouter, sheets: Optional[SheetsService] = None):
    """
    Factory: returns an async handler that parses args and routes the command.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        chat_id = str(update.effective_chat.id)
        args = context.args or []
        logger.info(
            "Command /%s from user %s (id=%s) args=%s",
            command_name, user.username or user.first_name, user.id, args
        )

        if not _check_access(chat_id, sheets):
            await update.message.reply_text(
                "⛔ Access denied. Your Telegram ID is not registered.\n"
                "Contact your administrator to be added to the system.",
                parse_mode="Markdown",
            )
            return

        if not args:
            await update.message.reply_text(
                f"Please provide a client name.\nUsage: `/{command_name.replace('-', '_')} [client name]`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text("⏳ Fetching data...", parse_mode="Markdown")

        response = await router.route(command_name, list(args))

        # Telegram has a 4096 char limit per message — split if needed
        for chunk in _split_message(response):
            await update.message.reply_text(chunk, parse_mode="Markdown")

    return handler


async def _start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm *Aureus*, your RM Copilot.\n\n"
        "I help you prepare for client meetings, review portfolios, "
        "and stay on top of next best actions.\n\n"
        "Type /help to see available commands.",
        parse_mode="Markdown",
    )


async def _help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


def _split_message(text: str, limit: int = 4000) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Split at last newline before limit
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
