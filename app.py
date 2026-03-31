"""
app.py

Aureus RM Copilot — application entry point.

Startup sequence:
  1. Load and validate configuration
  2. Connect to Google Sheets (or fall back to mock mode)
  3. Initialize Claude API service (optional — falls back to templates)
  4. Initialize services and command router
  5. Start the Telegram bot
"""

import logging
import sys

from services.config import load_config
from services.sheets_service import SheetsService, SheetsUnavailableError
from services.client_service import ClientService
from services.command_router import CommandRouter
from services.financial_analysis_service import FinancialAnalysisService
from services.equity_research_service import EquityResearchService
from bot.telegram_bot import build_application


def setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stdout,
    )


def main() -> None:
    # 1. Config
    try:
        config = load_config()
    except EnvironmentError as e:
        print(f"[STARTUP ERROR] {e}")
        sys.exit(1)

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Aureus RM Copilot | env=%s", config.app_env)

    # 2. Google Sheets connection
    sheets = None
    use_mock = False

    if not config.google_sheets_spreadsheet_id:
        logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not set — running in MOCK MODE.")
        use_mock = True
    else:
        try:
            sheets = SheetsService(
                credentials_path=config.google_application_credentials,
                spreadsheet_id=config.google_sheets_spreadsheet_id,
            )
            sheets.connect()
            logger.info("Google Sheets connected.")
        except SheetsUnavailableError as e:
            logger.warning("Google Sheets unavailable — running in MOCK MODE.\nReason: %s", e)
            use_mock = True

    # 3. Claude API service (optional)
    claude_service = None
    if config.claude_enabled:
        try:
            from services.claude_service import ClaudeService
            claude_service = ClaudeService(api_key=config.anthropic_api_key)
            logger.info("Claude API enabled | model=%s", claude_service.model)
        except Exception as e:
            logger.warning("Claude API init failed — responses will use templates. Error: %s", e)
    else:
        logger.info("ANTHROPIC_API_KEY not set — using template-based responses.")

    # 4. Services
    client_service = ClientService(sheets=sheets, use_mock=use_mock)
    # V3 — Core Financial Analysis Layer + Equity Research Plugin
    financial_analysis = FinancialAnalysisService()
    equity_research = EquityResearchService(financial_analysis=financial_analysis)
    logger.info("V3 services initialised | mock_universe=%s", financial_analysis.get_stock_universe())
    router = CommandRouter(
        client_service=client_service,
        claude_service=claude_service,
        sheets_service=sheets,
        financial_analysis=financial_analysis,
        equity_research=equity_research,
    )

    # 5. Telegram bot
    logger.info("Starting Telegram bot...")
    app = build_application(
        token=config.telegram_bot_token,
        router=router,
        sheets_service=sheets,
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
