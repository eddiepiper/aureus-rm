"""
scripts/bootstrap_v51_schema.py

One-time script to append V5.1 column headers to an existing live Google Sheet.

Run once to add the new fields introduced in V5.1 without disrupting existing data.
Existing columns are detected and skipped — only missing columns are appended.

Usage:
  python scripts/bootstrap_v51_schema.py

Required env vars (same as the main app):
  GOOGLE_APPLICATION_CREDENTIALS  — path to service account JSON
  GOOGLE_SHEETS_SPREADSHEET_ID    — spreadsheet ID
"""

import os
import sys

# Add project root to path so services can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sheets_service import SheetsService, SheetsUnavailableError

# V5.1 additions per tab
V51_NEW_COLUMNS = {
    "Customers": [
        "last_contact_date",
        "next_contact_due",
        "client_priority",
        "relationship_status",
        "attention_flag",
        "attention_reason",
        "deployment_style",   # may already exist — will be skipped if so
    ],
    "Interactions": [
        "discussion_tickers",
        "discussion_themes",
        "recommendation_given",
        "recommendation_status",
        "client_response",
        "meeting_required",
        "meeting_date",
        "created_by",
    ],
    "Tasks_NBA": [
        "linked_interaction_id",
        "linked_ticker",
        "task_category",
        "duplicate_key",
        "priority_score",
    ],
}


def bootstrap(sheets: SheetsService) -> None:
    import gspread

    wb = sheets._spreadsheet
    print(f"Connected to spreadsheet: {wb.title}")

    for tab_name, new_cols in V51_NEW_COLUMNS.items():
        try:
            ws: gspread.Worksheet = wb.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  [SKIP] Tab not found: {tab_name}")
            continue

        # Read current headers from row 1
        existing = ws.row_values(1)
        existing_lower = [str(h).lower().strip() for h in existing]

        added = []
        for col in new_cols:
            if col.lower() in existing_lower:
                continue
            next_col_index = len(existing) + len(added) + 1
            col_letter = _col_letter(next_col_index)
            ws.update(f"{col_letter}1", col)
            added.append(col)
            print(f"  [ADD] {tab_name} ← {col} (col {col_letter})")

        if not added:
            print(f"  [OK]  {tab_name} — all V5.1 columns already present")

    print("\nBootstrap complete.")


def _col_letter(n: int) -> str:
    """Convert 1-based column index to Excel-style column letter (A, B, ... Z, AA, AB ...)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


if __name__ == "__main__":
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials/service-account.json")
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")

    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_SPREADSHEET_ID environment variable not set.")
        sys.exit(1)

    sheets = SheetsService(credentials_path=creds, spreadsheet_id=spreadsheet_id)
    try:
        sheets.connect()
    except SheetsUnavailableError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    bootstrap(sheets)
