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
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from services.command_router import CommandRouter

logger = logging.getLogger(__name__)

HELP_TEXT = """
*Aureus RM Copilot*

Available commands:

/client-review [name]
_Full client review with holdings, interactions, and actions._

/portfolio-fit [name] [ticker]
_Check if a stock fits the client's portfolio and mandate._

/meeting-pack [name]
_Meeting prep pack with agenda and talking points._

/next-best-action [name]
_Suggested next actions for the RM._

/help — show this message
"""


def build_application(token: str, router: CommandRouter) -> Application:
    """
    Build and return the Telegram Application with all handlers registered.
    """
    app = Application.builder().token(token).build()

    # Bind handlers
    app.add_handler(CommandHandler("start", _start_handler))
    app.add_handler(CommandHandler("help", _help_handler))
    app.add_handler(CommandHandler("client_review", _make_command_handler("client-review", router)))
    app.add_handler(CommandHandler("portfolio_fit", _make_command_handler("portfolio-fit", router)))
    app.add_handler(CommandHandler("meeting_pack", _make_command_handler("meeting-pack", router)))
    app.add_handler(CommandHandler("next_best_action", _make_command_handler("next-best-action", router)))

    # Hyphenated aliases (Telegram supports underscores only in bot commands,
    # but we register both so the router handles either form)
    return app


def _make_command_handler(command_name: str, router: CommandRouter):
    """
    Factory: returns an async handler that parses args and routes the command.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        args = context.args or []
        logger.info(
            "Command /%s from user %s (id=%s) args=%s",
            command_name, user.username or user.first_name, user.id, args
        )

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
