"""
scripts/bootstrap_v7_ai_fields.py

Creates the AI_Assessment tab in the live Google Sheet for V7.

Safe to run on an existing spreadsheet:
  - If the tab already exists, only missing columns are added (idempotent)
  - If the tab does not exist, it is created with all headers in column order
  - Existing data is never modified

Usage:
  python scripts/bootstrap_v7_ai_fields.py

Required env vars (same as the main app):
  GOOGLE_APPLICATION_CREDENTIALS  — path to service account JSON
  GOOGLE_SHEETS_SPREADSHEET_ID    — spreadsheet ID
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sheets_service import SheetsService, SheetsUnavailableError

# ---------------------------------------------------------------------------
# V7 — AI_Assessment tab definition
# Column order must exactly match SheetsService.AI_ASSESSMENT_COLS
# ---------------------------------------------------------------------------

AI_ASSESSMENT_HEADERS = [
    # Customer identifiers
    "assessment_id", "customer_id", "customer_name",
    # Assessment metadata
    "assessment_date", "selected_criterion", "data_source", "source_is_internal",
    # Evidence
    "evidence_type", "evidence_date",
    # Income
    "annual_income", "income_currency", "income_period_start", "income_period_end",
    "income_source", "employer_name", "job_title",
    "salary_ytd", "bonus_ytd", "latest_noa_year", "latest_noa_amount",
    # DEPRECATED income field (backward-read only)
    "income_year",
    # Net personal assets (new explicit fields)
    "primary_residence_fmv", "primary_residence_secured_loan", "ownership_share_pct",
    "property_valuation_date",
    "other_personal_assets_value", "other_real_estate_value", "other_real_estate_secured_loans",
    "financial_assets_for_npa_value", "insurance_surrender_value",
    "business_interest_value", "other_personal_liabilities_value",
    "valuation_date", "statement_date",
    # DEPRECATED net assets fields (backward-read only)
    "total_assets", "total_liabilities", "net_assets",
    "property_value", "mortgage_liability", "financial_assets_networth",
    # Financial assets
    "total_financial_assets", "cash_holdings", "investment_holdings",
    "cpf_investment_amount", "funds_under_management_value",
    "financial_assets_related_liabilities",
    "margin_loan_balance", "portfolio_credit_line_balance",
    # FX
    "fx_rate_used", "fx_rate_date",
    # Joint account
    "joint_account_flag", "joint_account_note",
    # Decision output (filled after assessment)
    "recognised_amount_sgd", "threshold_sgd", "pass_result",
    "confidence_level", "assessment_status",
    "missing_fields", "inconsistency_flags",
    "manual_review_required", "manual_review_reasons",
    # Checker workflow
    "checker_status", "memo_text", "assessor_notes",
    # DEPRECATED metadata (backward-read only)
    "ai_selected_criteria",
    "last_updated",
]

TAB_NAME = "AI_Assessment"


def bootstrap(sheets: SheetsService) -> None:
    import gspread

    wb = sheets._spreadsheet
    print(f"Connected to spreadsheet: {wb.title}\n")

    # -----------------------------------------------------------------------
    # Check if the tab already exists
    # -----------------------------------------------------------------------
    existing_tabs = [ws.title for ws in wb.worksheets()]

    if TAB_NAME not in existing_tabs:
        print(f"  [CREATE] Tab '{TAB_NAME}' not found — creating...")
        ws = wb.add_worksheet(title=TAB_NAME, rows=1000, cols=len(AI_ASSESSMENT_HEADERS) + 5)
        # Write all headers in one call
        ws.update("A1", [AI_ASSESSMENT_HEADERS])
        print(f"  [OK]     '{TAB_NAME}' created with {len(AI_ASSESSMENT_HEADERS)} columns")
        print("\nBootstrap complete.")
        return

    # -----------------------------------------------------------------------
    # Tab exists — add only missing columns (idempotent)
    # -----------------------------------------------------------------------
    print(f"  [FOUND]  Tab '{TAB_NAME}' already exists — checking for missing columns...")
    ws: gspread.Worksheet = wb.worksheet(TAB_NAME)
    existing_headers = ws.row_values(1)
    existing_lower = [str(h).lower().strip() for h in existing_headers]

    added = []
    for col in AI_ASSESSMENT_HEADERS:
        if col.lower() in existing_lower:
            continue
        next_col_index = len(existing_headers) + len(added) + 1
        col_letter = _col_letter(next_col_index)
        ws.update(f"{col_letter}1", col)
        added.append(col)
        print(f"  [ADD]    {TAB_NAME} ← {col} (col {col_letter})")

    if not added:
        print(f"  [OK]     All V7 columns already present in '{TAB_NAME}'")

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
