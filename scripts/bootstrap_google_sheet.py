"""
scripts/bootstrap_google_sheet.py

One-time setup script for the Aureus RM Google Spreadsheet.

What it does:
  1. Connects to your Google Spreadsheet using the service account
  2. Creates (or clears) all 5 required tabs
  3. Writes the correct headers for each tab
  4. Inserts sample data for two clients:
       - CUST001: John Tan (Premier, Balanced) — 80% invested, 20% CASA
       - CUST002: Sarah Lim (Private, Growth) — 70% invested, 30% CASA

Run once before using the live Google Sheets integration:

    python scripts/bootstrap_google_sheet.py

Environment variables required (.env):
    GOOGLE_SHEETS_SPREADSHEET_ID
    GOOGLE_APPLICATION_CREDENTIALS

Portfolio structure:
  - Holdings tab models both invested positions and CASA liquidity
  - deployable_flag=Yes identifies CASA rows that can fund new ideas
  - No separate CASA tab — all positions (invested + liquid) are in Holdings
  - deployment_style on Customers guides how the RM frames deployment conversations
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "credentials/service-account.json",
)

# ---------------------------------------------------------------------------
# Tab schemas
# ---------------------------------------------------------------------------

TABS = {
    "Customers": [
        "customer_id", "telegram_chat_id", "full_name", "preferred_name",
        "mobile", "email", "country", "relationship_manager", "segment",
        "risk_profile", "investment_objective", "liquidity_needs",
        "investment_horizon", "preferred_markets", "restricted_markets",
        "esg_preference", "dividend_preference", "volatility_tolerance",
        "product_restrictions", "accreditation_status", "client_status",
        "onboarding_date", "last_review_date", "next_review_due",
        "notes_summary", "last_updated", "deployment_style",
    ],
    "Holdings": [
        # Core identifiers and position data
        "holding_id", "customer_id", "ticker", "security_name", "asset_class",
        "sector", "geography", "currency", "units", "avg_cost", "current_price",
        "market_value", "portfolio_weight_pct", "unrealized_pnl_pct",
        "income_yield_pct", "conviction_level", "last_updated",
        # Extended classification
        "status", "mandate_fit", "style_bucket", "suitability_checked",
        "liquidity_rating", "volatility_bucket", "instrument_type",
        "return_objective", "key_risk_note", "position_rationale",
        # Liquidity flag — Yes = CASA/deployable, No = invested holding
        "deployable_flag",
    ],
    "Interactions": [
        "interaction_id", "customer_id", "interaction_date", "channel",
        "interaction_type", "summary", "key_topics", "sentiment",
        "concern_level", "requested_action", "agent_response_summary",
        "follow_up_required", "follow_up_due", "owner", "last_updated",
    ],
    "Watchlist": [
        "watchlist_id", "customer_id", "ticker", "security_name",
        "reason_for_interest", "status", "added_date", "target_event",
        "note", "priority",
    ],
    "Tasks_NBA": [
        "task_id", "customer_id", "created_date", "task_type", "action_title",
        "action_detail", "rationale", "urgency", "status", "due_date",
        "owner", "source", "compliance_note", "completed_date", "outcome_note",
    ],
}

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_CUSTOMERS = [
    [
        "CUST001", "",  # telegram_chat_id — fill in after /start
        "John Tan", "John", "+65 9123 4567", "john.tan@email.com",
        "Singapore", "RM-01", "Premier", "Balanced", "Growth + Income",
        "Low", "5-7 years", "SG, US, HK", "",
        "No", "Yes", "Medium", "", "Accredited", "Active",
        "2020-01-15", "2024-09-01", "2025-03-01",
        "Client interested in dividend income. Cautious on China exposure.",
        "2024-11-01", "Phased",
    ],
    [
        "CUST002", "",
        "Sarah Lim", "Sarah", "+65 9234 5678", "sarah.lim@email.com",
        "Singapore", "RM-01", "Private", "Growth",
        "Capital Appreciation", "Low", "7-10 years", "SG, US, EU, HK", "",
        "Yes", "No", "High", "", "Accredited", "Active",
        "2019-06-01", "2024-10-15", "2025-04-15",
        "High conviction tech investor. Comfortable with volatility.",
        "2024-11-01", "Tactical",
    ],
]

# Holdings for John Tan (CUST001) — 80% invested, 20% CASA
# Holdings for Sarah Lim (CUST002) — 70% invested, 30% CASA
# deployable_flag=Yes marks CASA rows as deployable capital
SAMPLE_HOLDINGS = [
    # -----------------------------------------------------------------------
    # John Tan — CUST001 (total weight = 100%)
    # Invested: DBS 18.2 + UOB 8.9 + TSM 7.2 + OCBC 5.7 + MBH 10 + A35 10 + VWRD 10 + IGLB 10 = 80%
    # CASA: 20%
    # -----------------------------------------------------------------------
    ["H001", "CUST001", "D05.SI", "DBS Group Holdings", "Equity", "Financials",
     "Singapore", "SGD", 500, 30.50, 36.40, 18200.0, 18.2, 19.3, 5.8, "High", "2024-11-01",
     "Active", "Yes", "Income", "Yes", "Medium", "Medium", "Equity", "Income",
     "Rate-sensitive dividend exposure", "Core SG bank position", "No"],

    ["H002", "CUST001", "U11.SI", "UOB", "Equity", "Financials",
     "Singapore", "SGD", 300, 26.00, 29.80, 8940.0, 8.9, 14.6, 5.1, "Medium", "2024-11-01",
     "Active", "Yes", "Income", "Yes", "Medium", "Medium", "Equity", "Income",
     "Rate-sensitive dividend exposure", "Secondary SG bank position", "No"],

    ["H003", "CUST001", "TSM", "TSMC ADR", "Equity", "Technology",
     "US/Taiwan", "USD", 50, 110.00, 145.00, 7250.0, 7.2, 31.8, 1.5, "High", "2024-11-01",
     "Active", "Yes", "Growth", "Yes", "Medium", "High", "Equity", "Growth",
     "AI cycle and Taiwan risk", "Single-name growth exposure", "No"],

    ["H004", "CUST001", "O39.SI", "OCBC", "Equity", "Financials",
     "Singapore", "SGD", 400, 12.00, 14.20, 5680.0, 5.7, 18.3, 5.4, "Medium", "2024-11-01",
     "Active", "Yes", "Income", "Yes", "Medium", "Medium", "Equity", "Income",
     "Rate-sensitive dividend exposure", "Third SG bank holding", "No"],

    ["H008", "CUST001", "MBH.SI", "Nikko AM SGD Investment Grade Corporate Bond ETF",
     "ETF", "Fixed Income", "Singapore", "SGD", 1200, 1.00, 1.02, 1224.0, 10.0, 2.0, 3.2,
     "High", "2024-11-01",
     "Active", "Yes", "Income", "Yes", "High", "Low", "ETF", "Income",
     "Falling-rates positive", "Core SGD bond ballast", "No"],

    ["H009", "CUST001", "A35.SI", "ABF Singapore Bond Index Fund",
     "ETF", "Fixed Income", "Singapore", "SGD", 1500, 1.08, 1.10, 1650.0, 10.0, 1.9, 2.8,
     "High", "2024-11-01",
     "Active", "Yes", "Income", "Yes", "High", "Low", "ETF", "Income",
     "Falling-rates positive", "Second fixed income anchor", "No"],

    ["H010", "CUST001", "VWRD", "Vanguard FTSE All-World UCITS ETF",
     "ETF", "Global Equity", "Global", "USD", 40, 110.00, 118.00, 4720.0, 10.0, 7.3, 1.8,
     "Medium", "2024-11-01",
     "Active", "Yes", "Diversification", "Yes", "High", "Medium", "ETF", "Growth",
     "Broad global beta", "Non-SG diversification", "No"],

    ["H011", "CUST001", "IGLB", "iShares Global Govt Bond UCITS ETF",
     "ETF", "Fixed Income", "Global", "USD", 60, 48.00, 49.50, 2970.0, 10.0, 3.1, 2.4,
     "Medium", "2024-11-01",
     "Active", "No", "Defensive", "Yes", "High", "Low", "ETF", "Defensive",
     "Rates hedge", "Offshore duration diversifier", "No"],

    ["H012", "CUST001", "CASA-SGD", "SGD CASA Account",
     "Cash", "Cash", "Singapore", "SGD", 1, 30000.00, 30000.00, 30000.0, 20.0, 0.0, 0.05,
     "High", "2024-11-01",
     "Active", "Yes", "Liquidity", "Yes", "High", "Low", "CASA", "Liquidity",
     "Idle liquidity buffer", "Primary deployment pool", "Yes"],

    # -----------------------------------------------------------------------
    # Sarah Lim — CUST002 (total weight = 100%)
    # Invested: NVDA 35 + AAPL 20 + TSM 15 = 70%
    # CASA: 30%
    # -----------------------------------------------------------------------
    ["H005", "CUST002", "NVDA", "NVIDIA Corporation", "Equity", "Technology",
     "US", "USD", 100, 80.00, 132.00, 13200.0, 35.0, 65.0, 0.03, "High", "2024-11-01",
     "Active", "Yes", "AI", "Yes", "Medium", "High", "Equity", "Growth",
     "AI capex and valuation sensitivity", "Core AI winner", "No"],

    ["H006", "CUST002", "AAPL", "Apple Inc.", "Equity", "Technology",
     "US", "USD", 150, 155.00, 189.50, 28425.0, 20.0, 22.3, 0.5, "High", "2024-11-01",
     "Active", "Yes", "Platform Quality", "Yes", "Medium", "Medium", "Equity", "Growth",
     "Consumer platform resilience", "Core platform compounder", "No"],

    ["H007", "CUST002", "TSM", "TSMC ADR", "Equity", "Technology",
     "US/Taiwan", "USD", 100, 105.00, 145.00, 14500.0, 15.0, 38.1, 1.5, "High", "2024-11-01",
     "Active", "Yes", "Semiconductor", "Yes", "Medium", "High", "Equity", "Growth",
     "AI supply chain and geopolitical risk", "Semi supply chain exposure", "No"],

    ["H014", "CUST002", "CASA-USD", "USD CASA Account",
     "Cash", "Cash", "US", "USD", 1, 30000.00, 30000.00, 30000.0, 30.0, 0.0, 0.1,
     "High", "2024-11-01",
     "Active", "Yes", "Liquidity", "Yes", "High", "Low", "CASA", "Liquidity",
     "Idle liquidity buffer", "Dry powder for deployment", "Yes"],
]

SAMPLE_INTERACTIONS = [
    ["I001", "CUST001", "2024-11-15", "Phone", "Portfolio Review",
     "Quarterly review. Client happy with DBS performance. Queried about adding more tech exposure.",
     "Tech exposure, DBS performance", "Positive", "Low",
     "Send tech stock options", "Acknowledged — will prepare tech options",
     "Yes", "2024-12-01", "RM-01", "2024-11-15"],
    ["I002", "CUST001", "2024-10-03", "Email", "Product Enquiry",
     "Client asked about structured notes for income enhancement.",
     "Structured notes, income", "Neutral", "Low",
     "", "Sent product sheet", "No", "", "RM-01", "2024-10-03"],
    ["I003", "CUST002", "2024-11-20", "Meeting", "Portfolio Review",
     "Discussed NVDA earnings and AI theme. Client wants more ASEAN exposure.",
     "NVDA, AI, ASEAN", "Positive", "Low",
     "Explore ASEAN equity options", "Will prepare ASEAN equity brief",
     "Yes", "2024-12-05", "RM-01", "2024-11-20"],
]

SAMPLE_WATCHLIST = [
    ["W001", "CUST001", "AAPL", "Apple Inc.",
     "Client mentioned interest after reading about Apple Intelligence",
     "Monitoring", "2024-10-01", "Q1 2025 earnings", "", "Medium"],
    ["W002", "CUST002", "ASML", "ASML Holding",
     "Wants European semiconductor exposure as diversifier",
     "Monitoring", "2024-11-01", "", "", "High"],
]

SAMPLE_TASKS = [
    ["T001", "CUST001", "2024-11-15", "Follow-up", "Send tech exposure options",
     "Prepare 2-3 tech stock options consistent with balanced mandate",
     "Client expressed interest during Nov portfolio review",
     "Medium", "Open", "2024-12-15", "RM-01", "Client Request", "", "", ""],
    ["T002", "CUST002", "2024-11-20", "Research", "Prepare ASEAN equity brief",
     "Client wants ASEAN exposure — review SGX-listed and ASEAN ETF options",
     "Mentioned during Nov meeting",
     "Medium", "Open", "2024-12-05", "RM-01", "Client Request", "", "", ""],
]

# ---------------------------------------------------------------------------
# Bootstrap logic
# ---------------------------------------------------------------------------

def get_or_create_worksheet(spreadsheet, title: str, rows: int = 1000, cols: int = 35):
    """Return existing worksheet or create a new one."""
    try:
        ws = spreadsheet.worksheet(title)
        print(f"  Found existing tab: {title}")
        return ws
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        print(f"  Created new tab: {title}")
        return ws


def bootstrap():
    if not SPREADSHEET_ID:
        print("ERROR: GOOGLE_SHEETS_SPREADSHEET_ID not set in .env")
        sys.exit(1)

    print(f"Connecting to Google Sheets: {SPREADSHEET_ID}")
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"Connected: {spreadsheet.title}\n")

    tab_data = {
        "Customers":    (TABS["Customers"],    SAMPLE_CUSTOMERS),
        "Holdings":     (TABS["Holdings"],     SAMPLE_HOLDINGS),
        "Interactions": (TABS["Interactions"], SAMPLE_INTERACTIONS),
        "Watchlist":    (TABS["Watchlist"],    SAMPLE_WATCHLIST),
        "Tasks_NBA":    (TABS["Tasks_NBA"],    SAMPLE_TASKS),
    }

    for tab_name, (headers, sample_rows) in tab_data.items():
        print(f"Setting up tab: {tab_name}")
        ws = get_or_create_worksheet(spreadsheet, tab_name)

        # Clear and rewrite headers + sample data
        ws.clear()
        all_rows = [headers] + sample_rows
        ws.update("A1", all_rows)
        print(f"  Wrote {len(headers)} columns, {len(sample_rows)} sample rows\n")

    print("Bootstrap complete.")
    print("\nPortfolio structure:")
    print("  - John Tan: 80% invested (equities + ETFs + bonds) + 20% CASA-SGD")
    print("  - Sarah Lim: 70% invested (US tech equities) + 30% CASA-USD")
    print("  - deployable_flag=Yes rows are CASA holdings available for deployment")
    print("\nNext steps:")
    print("  1. Add your Telegram chat ID to the telegram_chat_id column in Customers")
    print("     (Send /start to your bot and check the logs for your chat ID)")
    print("  2. Set GOOGLE_SHEETS_SPREADSHEET_ID in .env")
    print("  3. Restart the bot: python app.py")


if __name__ == "__main__":
    bootstrap()
