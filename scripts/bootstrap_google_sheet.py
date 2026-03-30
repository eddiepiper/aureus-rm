"""
scripts/bootstrap_google_sheet.py

One-time setup script for the Aureus RM Google Spreadsheet.

What it does:
  1. Connects to your Google Spreadsheet using the service account
  2. Creates (or clears) all 5 required tabs
  3. Writes the correct headers for each tab
  4. Inserts sample data for two clients:
       - CUST001: John Tan (Premier, Balanced)
       - CUST002: Sarah Lim (Private, Growth)

Run once before using the live Google Sheets integration:

    python scripts/bootstrap_google_sheet.py

Environment variables required (.env):
    GOOGLE_SHEETS_SPREADSHEET_ID
    GOOGLE_APPLICATION_CREDENTIALS
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
        "notes_summary", "last_updated",
    ],
    "Holdings": [
        "holding_id", "customer_id", "ticker", "security_name", "asset_class",
        "sector", "geography", "currency", "units", "avg_cost", "current_price",
        "market_value", "portfolio_weight_pct", "unrealized_pnl_pct",
        "income_yield_pct", "conviction_level", "last_updated",
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
        "2024-11-01",
    ],
    [
        "CUST002", "",
        "Sarah Lim", "Sarah", "+65 9234 5678", "sarah.lim@email.com",
        "Singapore", "RM-01", "Private", "Growth",
        "Capital Appreciation", "Low", "7-10 years", "SG, US, EU, HK", "",
        "Yes", "No", "High", "", "Accredited", "Active",
        "2019-06-01", "2024-10-15", "2025-04-15",
        "High conviction tech investor. Comfortable with volatility.",
        "2024-11-01",
    ],
]

SAMPLE_HOLDINGS = [
    # John Tan — CUST001
    ["H001", "CUST001", "D05.SI", "DBS Group Holdings", "Equity", "Financials",
     "Singapore", "SGD", 500, 30.50, 36.40, 18200.0, 18.2, 19.3, 5.8, "High", "2024-11-01"],
    ["H002", "CUST001", "U11.SI", "UOB", "Equity", "Financials",
     "Singapore", "SGD", 300, 26.00, 29.80, 8940.0, 8.9, 14.6, 5.1, "Medium", "2024-11-01"],
    ["H003", "CUST001", "TSM", "TSMC ADR", "Equity", "Technology",
     "US/Taiwan", "USD", 50, 110.00, 145.00, 7250.0, 7.2, 31.8, 1.5, "High", "2024-11-01"],
    ["H004", "CUST001", "O39.SI", "OCBC", "Equity", "Financials",
     "Singapore", "SGD", 400, 12.00, 14.20, 5680.0, 5.7, 18.3, 5.4, "Medium", "2024-11-01"],
    # Sarah Lim — CUST002
    ["H005", "CUST002", "NVDA", "NVIDIA Corporation", "Equity", "Technology",
     "US", "USD", 100, 80.00, 132.00, 13200.0, 35.0, 65.0, 0.03, "High", "2024-11-01"],
    ["H006", "CUST002", "AAPL", "Apple Inc.", "Equity", "Technology",
     "US", "USD", 150, 155.00, 189.50, 28425.0, 20.0, 22.3, 0.5, "High", "2024-11-01"],
    ["H007", "CUST002", "TSM", "TSMC ADR", "Equity", "Technology",
     "US/Taiwan", "USD", 100, 105.00, 145.00, 14500.0, 15.0, 38.1, 1.5, "High", "2024-11-01"],
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

def get_or_create_worksheet(spreadsheet, title: str, rows: int = 1000, cols: int = 30):
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
    print("\nNext steps:")
    print("  1. Add your Telegram chat ID to the telegram_chat_id column in Customers")
    print("     (Send /start to your bot and check the logs for your chat ID)")
    print("  2. Set GOOGLE_SHEETS_SPREADSHEET_ID in .env")
    print("  3. Restart the bot: python app.py")


if __name__ == "__main__":
    bootstrap()
