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

# ---------------------------------------------------------------------------
# V3 — Mock stock universe (Phase 1)
# All data is framework-based and NOT real-time. Clearly labelled for RM use.
# ---------------------------------------------------------------------------

MOCK_STOCKS: dict[str, dict] = {
    "DBS": {
        "ticker": "DBS",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "DBS Group Holdings",
            "sector": "Financials",
            "geography": "Singapore",
            "market_cap_band": "Large Cap",
            "description": (
                "DBS Group is Southeast Asia's largest bank by assets, offering commercial "
                "banking, treasury, and wealth management services. Primary revenue from "
                "net interest income and fee-based wealth services."
            ),
        },
        "financials": {
            "revenue_ttm": "SGD 21.2B",
            "eps_ttm": "SGD 3.82",
            "pe_ratio": "9.5x",
            "pb_ratio": "1.6x",
            "roe_pct": "17.8%",
            "div_yield_pct": "5.8%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "SGD 5.8B",
            "revenue_est": "SGD 5.6B",
            "eps_actual": "SGD 1.02",
            "eps_est": "SGD 0.98",
            "beat_miss": "Beat",
            "guidance_direction": "Maintained",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "Rate environment supports NIM stability through 2025",
            "Wealth management AUM growth from regional HNW client flows",
            "Capital return programme — ongoing buybacks and dividend growth",
        ],
        "risks": [
            "NIM compression if rates are cut faster than expected",
            "Regional asset quality risk from China/HK property sector exposure",
        ],
        "thesis": {
            "bull_case": (
                "Best-in-class ROE in Singapore banking, strong capital position, "
                "and wealth management growth trajectory support premium valuation."
            ),
            "bear_case": (
                "Rate cuts will compress NIM materially; China property exposure "
                "remains an unresolved tail risk."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "Rapid rate cuts (100bps)",
                "impact": "Negative",
                "note": "NIM compression of ~20bps; earnings impact estimated at ~8% reduction.",
            },
            {
                "name": "Regional credit tightening",
                "impact": "Negative",
                "note": "Rising NPLs from SEA SME segment could require material provision build-up.",
            },
        ],
    },

    "UOB": {
        "ticker": "UOB",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "United Overseas Bank",
            "sector": "Financials",
            "geography": "Singapore / ASEAN",
            "market_cap_band": "Large Cap",
            "description": (
                "UOB is a leading ASEAN bank with strong retail and SME franchise "
                "across Singapore, Thailand, Malaysia, Indonesia, and Vietnam. "
                "Focus on ASEAN connectivity, trade finance, and regional expansion."
            ),
        },
        "financials": {
            "revenue_ttm": "SGD 14.1B",
            "eps_ttm": "SGD 2.94",
            "pe_ratio": "8.8x",
            "pb_ratio": "1.2x",
            "roe_pct": "14.2%",
            "div_yield_pct": "5.1%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "SGD 3.7B",
            "revenue_est": "SGD 3.6B",
            "eps_actual": "SGD 0.76",
            "eps_est": "SGD 0.74",
            "beat_miss": "Beat",
            "guidance_direction": "Maintained",
            "mgmt_tone": "Neutral",
        },
        "catalysts": [
            "Citi ASEAN integration nearing completion — cost synergies materialising",
            "ASEAN trade finance growth driven by supply chain relocation trends",
            "Digital banking expansion reducing cost-to-income ratio",
        ],
        "risks": [
            "Citi integration costs and execution risk remain elevated",
            "ASEAN credit cycle risk — rising household leverage in Thailand and Indonesia",
        ],
        "thesis": {
            "bull_case": (
                "ASEAN franchise and Citi acquisition create a differentiated regional bank "
                "with an improving ROE trajectory as integration costs normalise."
            ),
            "bear_case": (
                "Integration overhang, lower ROE vs. DBS, and ASEAN credit cycle risk "
                "cap near-term re-rating potential."
            ),
            "conviction": "Medium",
        },
        "scenarios": [
            {
                "name": "ASEAN growth slowdown",
                "impact": "Negative",
                "note": "Loan growth below 5% would pressure revenue; integration costs not yet recovered.",
            },
            {
                "name": "Citi integration delays",
                "impact": "Negative",
                "note": "Extended integration timeline increases execution risk and extends cost drag.",
            },
        ],
    },

    "AAPL": {
        "ticker": "AAPL",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "Apple Inc.",
            "sector": "Technology",
            "geography": "United States",
            "market_cap_band": "Mega Cap",
            "description": (
                "Apple designs and sells consumer electronics, software, and services "
                "including iPhone, Mac, iPad, wearables, and a growing services segment "
                "(App Store, iCloud, Apple TV+, Apple Pay). Services now exceed 25% of revenue."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 391B",
            "eps_ttm": "USD 6.57",
            "pe_ratio": "28.5x",
            "pb_ratio": "45.2x",
            "roe_pct": "160.9%",
            "div_yield_pct": "0.5%",
        },
        "earnings": {
            "quarter": "Q4 FY2025",
            "revenue_actual": "USD 94.9B",
            "revenue_est": "USD 94.1B",
            "eps_actual": "USD 1.64",
            "eps_est": "USD 1.60",
            "beat_miss": "Beat",
            "guidance_direction": "In-line",
            "mgmt_tone": "Neutral",
        },
        "catalysts": [
            "Apple Intelligence AI feature rollout driving upgrade cycle into FY2026",
            "Services segment margin expansion improving overall earnings quality",
            "India manufacturing ramp reducing US tariff exposure",
        ],
        "risks": [
            "China revenue (~18% of total) faces ongoing geopolitical and regulatory risk",
            "iPhone unit growth stagnating in core markets — upgrade cycle elongation",
        ],
        "thesis": {
            "bull_case": (
                "Services mix shift drives margin expansion and earnings quality; "
                "AI-driven upgrade supercycle could re-accelerate iPhone growth in FY2026-27."
            ),
            "bear_case": (
                "Premium valuation leaves little room for error; China risk and elongating "
                "upgrade cycles could compress multiples meaningfully."
            ),
            "conviction": "Medium",
        },
        "scenarios": [
            {
                "name": "China revenue disruption",
                "impact": "Negative",
                "note": "15% China revenue decline reduces group EPS by approximately 6%.",
            },
            {
                "name": "AI upgrade cycle underdelivers",
                "impact": "Negative",
                "note": "Flat iPhone units in FY2026 would disappoint consensus and pressure the multiple.",
            },
        ],
    },

    "NVDA": {
        "ticker": "NVDA",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "NVIDIA Corporation",
            "sector": "Technology",
            "geography": "United States",
            "market_cap_band": "Mega Cap",
            "description": (
                "NVIDIA designs GPUs and system-on-chip units. The Data Center segment "
                "(Hopper/Blackwell architectures) now dominates revenue, driven by AI training "
                "and inference demand from hyperscalers and enterprises."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 113B",
            "eps_ttm": "USD 2.53",
            "pe_ratio": "38.2x",
            "pb_ratio": "28.4x",
            "roe_pct": "123.8%",
            "div_yield_pct": "0.03%",
        },
        "earnings": {
            "quarter": "Q3 FY2026",
            "revenue_actual": "USD 35.1B",
            "revenue_est": "USD 33.2B",
            "eps_actual": "USD 0.89",
            "eps_est": "USD 0.84",
            "beat_miss": "Beat",
            "guidance_direction": "Raised",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "Blackwell architecture ramp — production yields improving, backlog clearing",
            "Sovereign AI and enterprise inference broadening demand beyond hyperscalers",
            "CUDA ecosystem lock-in remains a durable competitive moat",
        ],
        "risks": [
            "Valuation prices in significant future growth — any execution miss is severely punished",
            "Export controls to China limit a material revenue opportunity; regulatory risk remains elevated",
        ],
        "thesis": {
            "bull_case": (
                "AI compute infrastructure is a multi-year secular theme; NVDA is the dominant "
                "picks-and-shovels play with unmatched ecosystem and software advantages."
            ),
            "bear_case": (
                "Hyperscaler capex cycles are volatile; AMD and custom silicon competition "
                "is intensifying; current valuation requires flawless execution for years."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "AI capex pullback (20% cut)",
                "impact": "Very Negative",
                "note": "Hyperscaler capex cut would compress revenue growth and materially reset consensus.",
            },
            {
                "name": "Export control tightening",
                "impact": "Negative",
                "note": "Expanded China restrictions could remove ~10-15% of addressable market.",
            },
        ],
    },

    "TSM": {
        "ticker": "TSM",
        "is_mock": True,
        "data_freshness": "framework-based",
        "source_label": "MOCK / NOT REAL-TIME",
        "snapshot": {
            "name": "Taiwan Semiconductor Manufacturing Company",
            "sector": "Technology",
            "geography": "Taiwan / United States",
            "market_cap_band": "Large Cap",
            "description": (
                "TSMC is the world's largest dedicated contract chip manufacturer, producing "
                "chips for Apple, NVIDIA, AMD, and Qualcomm. Controls ~60% of global foundry "
                "revenue and over 90% of leading-edge node capacity."
            ),
        },
        "financials": {
            "revenue_ttm": "USD 88B",
            "eps_ttm": "USD 6.72",
            "pe_ratio": "22.4x",
            "pb_ratio": "6.8x",
            "roe_pct": "30.2%",
            "div_yield_pct": "1.4%",
        },
        "earnings": {
            "quarter": "Q3 2025",
            "revenue_actual": "USD 23.5B",
            "revenue_est": "USD 22.9B",
            "eps_actual": "USD 1.81",
            "eps_est": "USD 1.75",
            "beat_miss": "Beat",
            "guidance_direction": "Raised",
            "mgmt_tone": "Confident",
        },
        "catalysts": [
            "AI chip demand driving N3/N2 node utilisation from NVDA, AAPL, and custom silicon",
            "US fab buildout (Arizona) mitigates geopolitical risk and supports diversification",
            "Pricing power at leading nodes maintained — margins trending upward",
        ],
        "risks": [
            "Taiwan geopolitical risk is the primary overhang — impossible to fully hedge",
            "CapEx intensity is high and rising — free cash flow constrained during investment cycle",
        ],
        "thesis": {
            "bull_case": (
                "AI chip demand creates a multi-year capacity constraint at leading nodes; "
                "TSMC is the irreplaceable manufacturer with structural pricing power."
            ),
            "bear_case": (
                "Geopolitical risk is unquantifiable and could cause rapid multiple de-rating; "
                "CapEx cycle delays FCF recovery timeline."
            ),
            "conviction": "High",
        },
        "scenarios": [
            {
                "name": "Taiwan strait escalation",
                "impact": "Severe",
                "note": "Geopolitical escalation causes immediate multiple compression and global supply chain disruption.",
            },
            {
                "name": "AI demand deceleration",
                "impact": "Moderate Negative",
                "note": "N3/N2 utilisation softening compresses margins and requires capex revision.",
            },
        ],
    },
}
