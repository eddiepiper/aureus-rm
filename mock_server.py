"""
mock_server.py

Consolidated MCP server for local development.
Implements all Aureus tool stubs with realistic mock data.

Replaces all placeholder servers in .mcp.json during development.
Run by Claude Code when .mcp.json points to this file.

Usage (via .mcp.json):
  "command": "python"
  "args": ["mock_server.py"]

Tools exposed (seen by Claude Code as mcp__aureus_mock__<name>):
  CRM:         get_client_profile, get_recent_interactions
  Portfolio:   get_holdings, get_exposure_breakdown
  Suitability: get_risk_profile, validate_recommendation_framing
  Market:      get_company_snapshot, get_price_history
  Fundamentals:get_financials, get_estimates
  Research:    get_earnings_summary, search_news
  House View:  get_internal_view
  Compliance:  check_disclosures, get_approved_products
  Notes:       save_meeting_prep, save_action_item
"""

import json
import sys
import os

# Add project root to path so we can import services
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from services.mock_data import (
    MOCK_CUSTOMER,
    MOCK_HOLDINGS,
    MOCK_INTERACTIONS,
    MOCK_WATCHLIST,
    MOCK_TASKS,
)

mcp = FastMCP("aureus_mock")

# ------------------------------------------------------------------
# Mock stock data — clearly labeled as illustrative
# ------------------------------------------------------------------

MOCK_STOCKS = {
    "D05.SI": {
        "ticker": "D05.SI",
        "name": "DBS Group Holdings",
        "exchange": "SGX",
        "currency": "SGD",
        "sector": "Financials",
        "industry": "Banks — Diversified",
        "market_cap": 98_500_000_000,
        "description": (
            "DBS Group Holdings is Singapore's largest bank by assets and one of Southeast "
            "Asia's leading financial institutions. The group operates across consumer banking, "
            "institutional banking, treasury markets, and wealth management across Singapore, "
            "Hong Kong, China, India, and Indonesia."
        ),
        "price_current": 36.40,
        "price_3m_ago": 34.95,
        "price_1y_ago": 32.60,
        "return_3m_pct": 4.2,
        "return_1y_pct": 11.8,
        "ytd_pct": 6.1,
        "revenue_ttm": 16_800_000_000,
        "revenue_growth_yoy_pct": 8.2,
        "ebitda_margin_pct": None,  # not standard for banks
        "net_income_ttm": 10_300_000_000,
        "eps_ttm": 3.94,
        "pe_ratio": 9.2,
        "pb_ratio": 1.7,
        "roe_pct": 18.4,
        "dividend_yield_pct": 5.8,
        "revenue_next_fy": 17_200_000_000,
        "eps_next_fy": 3.98,
        "consensus_rating": "Buy",
        "num_analysts": 19,
        "price_target_median": 39.00,
        "price_target_low": 34.00,
        "price_target_high": 43.00,
        "house_view_rating": "Overweight",
        "house_view_summary": (
            "DBS remains our preferred Singapore bank exposure given best-in-class ROE, "
            "strong capital position (CET1 14.1%), and digital franchise optionality. "
            "Key risk to monitor: NIM trajectory in H2 2025."
        ),
        "house_view_last_updated": "2024-11-01",
    },
    "U11.SI": {
        "ticker": "U11.SI",
        "name": "United Overseas Bank",
        "exchange": "SGX",
        "currency": "SGD",
        "sector": "Financials",
        "industry": "Banks — Diversified",
        "market_cap": 47_200_000_000,
        "description": (
            "United Overseas Bank (UOB) is one of Singapore's three major banks, with a "
            "particularly strong ASEAN franchise focused on SME and retail banking across "
            "Thailand, Malaysia, Indonesia, and Vietnam. UOB completed the acquisition of "
            "Citigroup's consumer banking operations in four ASEAN markets in 2023."
        ),
        "price_current": 29.80,
        "price_3m_ago": 28.40,
        "price_1y_ago": 27.10,
        "return_3m_pct": 4.9,
        "return_1y_pct": 10.0,
        "ytd_pct": 5.5,
        "revenue_ttm": 11_200_000_000,
        "revenue_growth_yoy_pct": 11.5,
        "ebitda_margin_pct": None,
        "net_income_ttm": 5_700_000_000,
        "eps_ttm": 3.41,
        "pe_ratio": 8.7,
        "pb_ratio": 1.3,
        "roe_pct": 14.1,
        "dividend_yield_pct": 5.1,
        "revenue_next_fy": 11_800_000_000,
        "eps_next_fy": 3.55,
        "consensus_rating": "Hold",
        "num_analysts": 16,
        "price_target_median": 31.00,
        "price_target_low": 27.00,
        "price_target_high": 35.00,
        "house_view_rating": "Neutral",
        "house_view_summary": (
            "UOB's ASEAN expansion provides long-term growth optionality, but near-term "
            "integration costs and NIM pressure limit re-rating potential. Dividend yield "
            "remains supportive."
        ),
        "house_view_last_updated": "2024-10-15",
    },
    "TSM": {
        "ticker": "TSM",
        "name": "Taiwan Semiconductor Manufacturing Company",
        "exchange": "NYSE",
        "currency": "USD",
        "sector": "Technology",
        "industry": "Semiconductors",
        "market_cap": 760_000_000_000,
        "description": (
            "TSMC is the world's largest dedicated independent semiconductor foundry, "
            "manufacturing chips for Apple, Nvidia, AMD, and most of the semiconductor "
            "industry. TSMC operates the leading-edge N3 and N5 process nodes and is the "
            "critical gating factor in global AI and advanced computing supply chains."
        ),
        "price_current": 145.00,
        "price_3m_ago": 128.50,
        "price_1y_ago": 108.00,
        "return_3m_pct": 12.8,
        "return_1y_pct": 34.3,
        "ytd_pct": 18.4,
        "revenue_ttm": 72_700_000_000,
        "revenue_growth_yoy_pct": 27.6,
        "ebitda_margin_pct": 52.4,
        "net_income_ttm": 28_300_000_000,
        "eps_ttm": 5.48,
        "pe_ratio": 26.5,
        "pb_ratio": 7.2,
        "roe_pct": 28.1,
        "dividend_yield_pct": 1.5,
        "revenue_next_fy": 88_000_000_000,
        "eps_next_fy": 6.80,
        "consensus_rating": "Buy",
        "num_analysts": 32,
        "price_target_median": 175.00,
        "price_target_low": 140.00,
        "price_target_high": 220.00,
        "house_view_rating": "Overweight",
        "house_view_summary": (
            "TSMC is a structural beneficiary of AI-driven semiconductor demand. "
            "Leading-edge node monopoly and pricing power support margin expansion. "
            "Key risk: Taiwan geopolitical risk and capex intensity."
        ),
        "house_view_last_updated": "2024-11-10",
    },
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3_100_000_000_000,
        "description": (
            "Apple designs, manufactures, and markets smartphones, personal computers, "
            "tablets, wearables, and accessories, and sells a variety of related services. "
            "The iPhone accounts for approximately 52% of revenue. Services (App Store, "
            "iCloud, Apple Pay) is the fastest-growing and highest-margin segment."
        ),
        "price_current": 189.50,
        "price_3m_ago": 178.20,
        "price_1y_ago": 165.00,
        "return_3m_pct": 6.3,
        "return_1y_pct": 14.8,
        "ytd_pct": 9.1,
        "revenue_ttm": 391_000_000_000,
        "revenue_growth_yoy_pct": 2.8,
        "ebitda_margin_pct": 33.4,
        "net_income_ttm": 100_300_000_000,
        "eps_ttm": 6.57,
        "pe_ratio": 28.8,
        "pb_ratio": 48.5,
        "roe_pct": 160.6,
        "dividend_yield_pct": 0.5,
        "revenue_next_fy": 405_000_000_000,
        "eps_next_fy": 7.14,
        "consensus_rating": "Buy",
        "num_analysts": 42,
        "price_target_median": 215.00,
        "price_target_low": 175.00,
        "price_target_high": 260.00,
        "house_view_rating": "Neutral",
        "house_view_summary": (
            "Apple's services growth and ecosystem stickiness are structural positives. "
            "Hardware cycle recovery is slower than expected. Valuation at 29x earnings "
            "leaves limited upside without a clearer AI monetization catalyst."
        ),
        "house_view_last_updated": "2024-10-28",
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Technology",
        "industry": "Semiconductors",
        "market_cap": 2_950_000_000_000,
        "description": (
            "NVIDIA designs graphics processing units (GPUs) and system-on-chip units. "
            "Its Data Center segment (Hopper/Blackwell GPU platforms) is the dominant "
            "hardware for AI training and inference workloads globally. NVIDIA also operates "
            "gaming, professional visualization, and automotive segments."
        ),
        "price_current": 132.00,
        "price_3m_ago": 108.00,
        "price_1y_ago": 49.50,
        "return_3m_pct": 22.2,
        "return_1y_pct": 166.7,
        "ytd_pct": 43.1,
        "revenue_ttm": 96_300_000_000,
        "revenue_growth_yoy_pct": 194.0,
        "ebitda_margin_pct": 64.8,
        "net_income_ttm": 53_000_000_000,
        "eps_ttm": 2.16,
        "pe_ratio": 61.1,
        "pb_ratio": 55.0,
        "roe_pct": 123.8,
        "dividend_yield_pct": 0.03,
        "revenue_next_fy": 130_000_000_000,
        "eps_next_fy": 2.97,
        "consensus_rating": "Buy",
        "num_analysts": 50,
        "price_target_median": 175.00,
        "price_target_low": 100.00,
        "price_target_high": 220.00,
        "house_view_rating": "Overweight",
        "house_view_summary": (
            "NVIDIA remains the dominant AI infrastructure play with Blackwell ramp "
            "driving continued data center growth. High valuation and execution risk "
            "on supply chain make this suitable for growth-oriented mandates only."
        ),
        "house_view_last_updated": "2024-11-20",
    },
}

MOCK_NEWS = {
    "D05.SI": [
        {"date": "2024-11-28", "headline": "DBS Q3 net profit rises 15% to SGD 3.0B, beats estimates", "source": "Bloomberg"},
        {"date": "2024-11-15", "headline": "DBS raises quarterly dividend to SGD 0.54 per share", "source": "Reuters"},
        {"date": "2024-10-30", "headline": "DBS CEO signals NIM stability through H1 2025", "source": "Straits Times"},
    ],
    "U11.SI": [
        {"date": "2024-11-26", "headline": "UOB Q3 profit SGD 1.61B, up 11% YoY on ASEAN expansion", "source": "Bloomberg"},
        {"date": "2024-11-10", "headline": "UOB completes Citi ASEAN integration ahead of schedule", "source": "Reuters"},
    ],
    "TSM": [
        {"date": "2024-11-25", "headline": "TSMC November sales surge 34% YoY on AI chip demand", "source": "DigiTimes"},
        {"date": "2024-11-18", "headline": "TSMC N2 node yield improving faster than expected — analysts", "source": "Bloomberg"},
        {"date": "2024-11-05", "headline": "TSMC raises 2025 capex guidance to $36B amid AI demand", "source": "Reuters"},
    ],
    "AAPL": [
        {"date": "2024-11-20", "headline": "Apple Intelligence features launching in 18 countries", "source": "Apple Newsroom"},
        {"date": "2024-11-08", "headline": "iPhone 16 sell-through broadly in line with iPhone 15", "source": "Barclays Research"},
    ],
    "NVDA": [
        {"date": "2024-11-29", "headline": "NVIDIA Q3 revenue $35.1B, beats estimates by 6%; Blackwell demand strong", "source": "Bloomberg"},
        {"date": "2024-11-29", "headline": "NVIDIA guides Q4 revenue $37.5B — above consensus", "source": "Reuters"},
        {"date": "2024-11-20", "headline": "NVIDIA Blackwell shipment delays resolved — supply now ramping", "source": "The Information"},
    ],
}

MOCK_EARNINGS = {
    "D05.SI_Q3FY2024": {
        "ticker": "D05.SI",
        "quarter": "Q3FY2024",
        "report_date": "2024-11-04",
        "headline_revenue": 5_780_000_000,
        "headline_eps": 1.09,
        "consensus_revenue": 5_620_000_000,
        "consensus_eps": 1.04,
        "beat_miss_revenue": "Beat by 2.8%",
        "beat_miss_eps": "Beat by 4.8%",
        "guidance_summary": "Management maintained FY2024 return on equity guidance of ~18%. NIM expected to remain stable near term.",
        "management_tone": "Confident. CEO cited resilient loan growth, strong wealth management inflows, and improving fee income as key positives.",
        "key_changes": "NIM guidance subtly softened for 2025. Credit costs remain benign. Fee income growth accelerated.",
    },
}

# ------------------------------------------------------------------
# CRM Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_client_profile(client_name: str = "", client_id: str = "") -> str:
    """
    Retrieve structured client profile from CRM.
    Accepts client_name (partial match, case-insensitive) or client_id.
    Returns client profile including risk profile, segment, AUM band, and mandate details.
    """
    # Simple name match against mock data
    if client_name.lower() in MOCK_CUSTOMER["full_name"].lower():
        return json.dumps(MOCK_CUSTOMER)
    if client_id == MOCK_CUSTOMER["customer_id"]:
        return json.dumps(MOCK_CUSTOMER)
    return json.dumps({
        "error": f"No client found matching name='{client_name}' or id='{client_id}'",
        "available_mock_clients": [MOCK_CUSTOMER["full_name"]],
    })


@mcp.tool()
def get_recent_interactions(client_id: str, limit: int = 5) -> str:
    """
    Retrieve recent CRM interaction history for a client.
    Returns interactions sorted by date descending, including follow-up status.
    """
    interactions = [i for i in MOCK_INTERACTIONS if i["customer_id"] == client_id]
    return json.dumps(interactions[:limit])


# ------------------------------------------------------------------
# Portfolio Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_holdings(client_id: str) -> str:
    """
    Retrieve current portfolio holdings for a client.
    Returns list of holdings with ticker, sector, market value, weight, and P&L.
    """
    holdings = [h for h in MOCK_HOLDINGS if h["customer_id"] == client_id]
    return json.dumps({
        "client_id": client_id,
        "holdings": holdings,
        "total_holdings": len(holdings),
        "currency": "SGD",
        "as_of_date": "2024-11-30",
        "note": "MOCK DATA — illustrative only",
    })


@mcp.tool()
def get_exposure_breakdown(client_id: str) -> str:
    """
    Retrieve portfolio exposure breakdown by sector, geography, and asset class.
    """
    holdings = [h for h in MOCK_HOLDINGS if h["customer_id"] == client_id]
    by_sector: dict = {}
    by_geo: dict = {}
    by_asset: dict = {}
    for h in holdings:
        w = float(h.get("portfolio_weight_pct", 0))
        by_sector[h.get("sector", "Other")] = round(by_sector.get(h.get("sector", "Other"), 0) + w, 2)
        by_geo[h.get("geography", "Other")] = round(by_geo.get(h.get("geography", "Other"), 0) + w, 2)
        by_asset[h.get("asset_class", "Equity")] = round(by_asset.get(h.get("asset_class", "Equity"), 0) + w, 2)
    return json.dumps({
        "client_id": client_id,
        "by_sector": by_sector,
        "by_geography": by_geo,
        "by_asset_class": by_asset,
        "note": "MOCK DATA — illustrative only",
    })


# ------------------------------------------------------------------
# Suitability Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_risk_profile(client_id: str) -> str:
    """
    Retrieve client suitability risk profile and investment mandate constraints.
    Returns risk rating, investment horizon, concentration limits, and exclusions.
    """
    if client_id == MOCK_CUSTOMER["customer_id"]:
        return json.dumps({
            "client_id": client_id,
            "risk_rating": MOCK_CUSTOMER["risk_profile"].lower(),
            "investment_horizon": MOCK_CUSTOMER["investment_horizon"],
            "investment_objective": MOCK_CUSTOMER["investment_objective"],
            "max_single_name_pct": 15.0,
            "max_sector_pct": 20.0,
            "excluded_sectors": [],
            "excluded_geographies": [],
            "liquidity_requirement": "Low — no near-term liquidity event",
            "esg_preference": MOCK_CUSTOMER["esg_preference"],
            "dividend_preference": MOCK_CUSTOMER["dividend_preference"],
            "volatility_tolerance": MOCK_CUSTOMER["volatility_tolerance"],
            "accreditation_status": MOCK_CUSTOMER["accreditation_status"],
            "last_review_date": MOCK_CUSTOMER["last_review_date"],
            "note": "MOCK DATA — illustrative only",
        })
    return json.dumps({"error": f"No risk profile found for client_id={client_id}"})


@mcp.tool()
def validate_recommendation_framing(text: str, context: str = "") -> str:
    """
    Validate that output language meets internal compliance framing requirements.
    Checks for prohibited language and returns pass/fail with flagged phrases.
    """
    import re
    prohibited = [
        (r"guaranteed (return|income|profit|gain)", "block"),
        (r"risk[\s-]free", "block"),
        (r"will definitely", "block"),
        (r"certain to", "block"),
        (r"can'?t lose", "block"),
        (r"no[\s-]brainer", "block"),
        (r"you should buy", "block"),
        (r"sure thing", "block"),
        (r"100% (sure|certain|safe)", "block"),
    ]
    flags = []
    for pattern, severity in prohibited:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            flags.append({"pattern": pattern, "matched": m.group(), "severity": severity})
    return json.dumps({"passed": len(flags) == 0, "flags": flags})


# ------------------------------------------------------------------
# Market Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_company_snapshot(ticker: str) -> str:
    """
    Retrieve company overview: business description, sector, market cap, key identifiers.
    Supports: D05.SI, U11.SI, TSM, AAPL, NVDA.
    """
    stock = MOCK_STOCKS.get(ticker.upper())
    if not stock:
        return json.dumps({
            "error": f"No mock data available for ticker '{ticker}'",
            "available_tickers": list(MOCK_STOCKS.keys()),
        })
    return json.dumps({
        "ticker": stock["ticker"],
        "name": stock["name"],
        "exchange": stock["exchange"],
        "currency": stock["currency"],
        "sector": stock["sector"],
        "industry": stock["industry"],
        "market_cap": stock["market_cap"],
        "description": stock["description"],
        "note": "MOCK DATA — illustrative only",
    })


@mcp.tool()
def get_price_history(ticker: str, period: str = "1y") -> str:
    """
    Retrieve price performance summary for a ticker.
    Period options: 3m, 1y, ytd.
    Returns current price, period-ago price, and return percentages.
    """
    stock = MOCK_STOCKS.get(ticker.upper())
    if not stock:
        return json.dumps({"error": f"No mock data for ticker '{ticker}'"})
    return json.dumps({
        "ticker": stock["ticker"],
        "price_current": stock["price_current"],
        "price_3m_ago": stock["price_3m_ago"],
        "price_1y_ago": stock["price_1y_ago"],
        "return_3m_pct": stock["return_3m_pct"],
        "return_1y_pct": stock["return_1y_pct"],
        "ytd_pct": stock["ytd_pct"],
        "currency": stock["currency"],
        "note": "MOCK DATA — illustrative only",
    })


# ------------------------------------------------------------------
# Fundamentals Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_financials(ticker: str, period: str = "ttm") -> str:
    """
    Retrieve income statement and key financial metrics for a ticker.
    Period: ttm (trailing twelve months), annual, quarterly.
    """
    stock = MOCK_STOCKS.get(ticker.upper())
    if not stock:
        return json.dumps({"error": f"No mock financials for ticker '{ticker}'"})
    return json.dumps({
        "ticker": stock["ticker"],
        "period": period,
        "revenue": stock["revenue_ttm"],
        "revenue_growth_yoy_pct": stock["revenue_growth_yoy_pct"],
        "ebitda_margin_pct": stock["ebitda_margin_pct"],
        "net_income": stock["net_income_ttm"],
        "eps": stock["eps_ttm"],
        "pe_ratio": stock["pe_ratio"],
        "pb_ratio": stock["pb_ratio"],
        "roe_pct": stock["roe_pct"],
        "dividend_yield_pct": stock["dividend_yield_pct"],
        "currency": stock["currency"],
        "note": "MOCK DATA — illustrative only",
    })


@mcp.tool()
def get_estimates(ticker: str) -> str:
    """
    Retrieve analyst consensus estimates: revenue, EPS, price targets, and rating distribution.
    """
    stock = MOCK_STOCKS.get(ticker.upper())
    if not stock:
        return json.dumps({"error": f"No mock estimates for ticker '{ticker}'"})
    return json.dumps({
        "ticker": stock["ticker"],
        "revenue_next_fy": stock["revenue_next_fy"],
        "eps_next_fy": stock["eps_next_fy"],
        "consensus_rating": stock["consensus_rating"],
        "num_analysts": stock["num_analysts"],
        "price_target_median": stock["price_target_median"],
        "price_target_low": stock["price_target_low"],
        "price_target_high": stock["price_target_high"],
        "currency": stock["currency"],
        "note": "MOCK DATA — analyst estimates are not guaranteed",
    })


# ------------------------------------------------------------------
# Research Tools
# ------------------------------------------------------------------

@mcp.tool()
def get_earnings_summary(ticker: str, quarter: str = "") -> str:
    """
    Retrieve earnings summary for a specific quarter.
    Returns headline results, beat/miss vs consensus, management tone, and key changes.
    """
    key = f"{ticker.upper()}_{quarter.upper()}"
    earnings = MOCK_EARNINGS.get(key)
    if not earnings:
        # Return latest available if no specific quarter
        available = [k for k in MOCK_EARNINGS if k.startswith(ticker.upper())]
        if available:
            earnings = MOCK_EARNINGS[available[0]]
        else:
            return json.dumps({
                "error": f"No earnings data for {ticker} {quarter}",
                "available": list(MOCK_EARNINGS.keys()),
            })
    return json.dumps({**earnings, "note": "MOCK DATA — illustrative only"})


@mcp.tool()
def search_news(ticker: str, days_back: int = 30) -> str:
    """
    Search recent news articles and announcements for a ticker.
    Returns headlines, dates, and source attribution.
    """
    news = MOCK_NEWS.get(ticker.upper(), [])
    if not news:
        return json.dumps({
            "ticker": ticker,
            "articles": [],
            "note": f"No mock news available for {ticker}. Available: {list(MOCK_NEWS.keys())}",
        })
    return json.dumps({
        "ticker": ticker,
        "articles": news,
        "note": "MOCK DATA — illustrative only",
    })


# ------------------------------------------------------------------
# House View Tool
# ------------------------------------------------------------------

@mcp.tool()
def get_internal_view(ticker: str = "", sector: str = "") -> str:
    """
    Retrieve internal house view rating and commentary for a ticker or sector.
    Returns: rating (Overweight/Neutral/Underweight), summary, and last updated date.
    Clearly labeled as internal view — not a public analyst recommendation.
    """
    stock = MOCK_STOCKS.get(ticker.upper())
    if not stock:
        return json.dumps({
            "available": False,
            "ticker": ticker,
            "note": f"No internal house view for '{ticker}'. Available: {list(MOCK_STOCKS.keys())}",
        })
    return json.dumps({
        "available": True,
        "ticker": stock["ticker"],
        "rating": stock["house_view_rating"],
        "summary": stock["house_view_summary"],
        "last_updated": stock["house_view_last_updated"],
        "label": "INTERNAL HOUSE VIEW — not for external distribution",
        "note": "MOCK DATA — illustrative only",
    })


# ------------------------------------------------------------------
# Compliance Tools
# ------------------------------------------------------------------

@mcp.tool()
def check_disclosures(ticker: str, product_type: str = "equity") -> str:
    """
    Check whether compliance disclosures or distribution restrictions apply for a ticker.
    """
    # Mock: no restrictions on standard Singapore/US equities
    return json.dumps({
        "ticker": ticker.upper(),
        "disclosures_required": False,
        "disclosure_list": [],
        "distribution_restrictions": [],
        "approved_for_accredited_investors": True,
        "note": "MOCK DATA — always verify with compliance team before client discussion",
    })


@mcp.tool()
def get_approved_products(client_segment: str = "") -> str:
    """
    Retrieve list of product types approved for distribution to the given client segment.
    """
    return json.dumps({
        "client_segment": client_segment or "default",
        "approved_product_types": [
            "SGX-listed equities",
            "NYSE/NASDAQ-listed equities",
            "Singapore Government Securities",
            "Investment Grade Bonds",
            "Unit Trusts (MAS-registered)",
            "Exchange Traded Funds",
        ],
        "note": "MOCK DATA — consult compliance for actual approved product list",
    })


# ------------------------------------------------------------------
# Notes Tools
# ------------------------------------------------------------------

@mcp.tool()
def save_meeting_prep(client_id: str, content: str, meeting_date: str = "", created_by: str = "RM") -> str:
    """
    Save a structured meeting prep note to the internal notes system.
    In mock mode, acknowledges receipt without persisting to any system.
    """
    import datetime
    return json.dumps({
        "success": True,
        "record_id": f"MOCK-{client_id}-{datetime.date.today().isoformat()}",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": "MOCK: Note acknowledged but not persisted. Wire notes.save_meeting_prep to CRM for live logging.",
    })


@mcp.tool()
def save_action_item(client_id: str, action: str, priority: str = "medium", due_date: str = "") -> str:
    """
    Log a next-best-action item to the workflow system.
    In mock mode, acknowledges receipt without persisting.
    """
    import datetime
    return json.dumps({
        "success": True,
        "record_id": f"MOCK-TASK-{client_id}-{datetime.date.today().isoformat()}",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": "MOCK: Task acknowledged but not persisted.",
    })


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
