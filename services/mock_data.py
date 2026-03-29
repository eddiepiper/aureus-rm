"""
services/mock_data.py

Fallback mock data for local development when Google Sheets is unavailable.
Clearly labeled as MOCK in all outputs. Never used in production.
"""

MOCK_CUSTOMER = {
    "customer_id": "CUST001",
    "telegram_chat_id": "",
    "full_name": "John Tan",
    "preferred_name": "John",
    "segment": "Premier",
    "risk_profile": "Balanced",
    "investment_objective": "Growth + Income",
    "investment_horizon": "5-7 years",
    "liquidity_needs": "Low",
    "preferred_markets": "SG, US, HK",
    "restricted_markets": "",
    "esg_preference": "No",
    "dividend_preference": "Yes",
    "volatility_tolerance": "Medium",
    "accreditation_status": "Accredited",
    "client_status": "Active",
    "last_review_date": "2024-09-01",
    "next_review_due": "2025-03-01",
    "notes_summary": "Client interested in dividend income. Cautious about China exposure.",
}

MOCK_HOLDINGS = [
    {
        "holding_id": "H001",
        "customer_id": "CUST001",
        "ticker": "D05.SI",
        "security_name": "DBS Group Holdings",
        "asset_class": "Equity",
        "sector": "Financials",
        "geography": "Singapore",
        "currency": "SGD",
        "units": 500,
        "avg_cost": 30.50,
        "current_price": 36.40,
        "market_value": 18200.0,
        "portfolio_weight_pct": 18.2,
        "unrealized_pnl_pct": 19.3,
        "income_yield_pct": 5.8,
        "conviction_level": "High",
    },
    {
        "holding_id": "H002",
        "customer_id": "CUST001",
        "ticker": "U11.SI",
        "security_name": "UOB",
        "asset_class": "Equity",
        "sector": "Financials",
        "geography": "Singapore",
        "currency": "SGD",
        "units": 300,
        "avg_cost": 26.00,
        "current_price": 29.80,
        "market_value": 8940.0,
        "portfolio_weight_pct": 8.9,
        "unrealized_pnl_pct": 14.6,
        "income_yield_pct": 5.1,
        "conviction_level": "Medium",
    },
    {
        "holding_id": "H003",
        "customer_id": "CUST001",
        "ticker": "TSM",
        "security_name": "TSMC ADR",
        "asset_class": "Equity",
        "sector": "Technology",
        "geography": "US/Taiwan",
        "currency": "USD",
        "units": 50,
        "avg_cost": 110.00,
        "current_price": 145.00,
        "market_value": 7250.0,
        "portfolio_weight_pct": 7.2,
        "unrealized_pnl_pct": 31.8,
        "income_yield_pct": 1.5,
        "conviction_level": "High",
    },
]

MOCK_INTERACTIONS = [
    {
        "interaction_id": "I001",
        "customer_id": "CUST001",
        "interaction_date": "2024-11-15",
        "channel": "Phone",
        "interaction_type": "Portfolio Review",
        "summary": "Quarterly review. Client happy with DBS performance. Queried about adding more tech exposure.",
        "follow_up_required": "Yes",
        "follow_up_due": "2024-12-01",
        "owner": "RM",
    },
    {
        "interaction_id": "I002",
        "customer_id": "CUST001",
        "interaction_date": "2024-10-03",
        "channel": "Email",
        "interaction_type": "Product Enquiry",
        "summary": "Client asked about structured notes for income enhancement.",
        "follow_up_required": "No",
        "follow_up_due": "",
        "owner": "RM",
    },
]

MOCK_WATCHLIST = [
    {
        "watchlist_id": "W001",
        "customer_id": "CUST001",
        "ticker": "AAPL",
        "security_name": "Apple Inc",
        "reason_for_interest": "Client mentioned interest after reading news about AI features",
        "status": "Monitoring",
        "priority": "Medium",
    },
]

MOCK_TASKS = [
    {
        "task_id": "T001",
        "customer_id": "CUST001",
        "task_type": "Follow-up",
        "action_title": "Send tech exposure options",
        "action_detail": "Prepare 2-3 tech stock options consistent with balanced mandate",
        "rationale": "Client expressed interest in tech during Nov portfolio review",
        "urgency": "Medium",
        "status": "Open",
        "due_date": "2024-12-15",
        "owner": "RM",
    },
]
