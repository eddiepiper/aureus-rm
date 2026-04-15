"""Unit tests for NBAAgent scoring logic (V5.1)."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from services.nba_agent import NBAAgent, SIGNAL_SCORES


@pytest.fixture
def nba():
    return NBAAgent(claude_service=MagicMock(), relationship_memory=None)


def _customer(cid="C001", next_review=None):
    c = {"customer_id": cid, "full_name": "Test Client"}
    if next_review:
        c["next_review_due"] = next_review
    return c


def _rel_ctx(overdue=None, days_since=None, pending_recs=None, open_tasks=None, watchlist=None):
    return {
        "overdue_tasks": overdue or [],
        "days_since_last_contact": days_since,
        "pending_recommendations": pending_recs or [],
        "open_tasks": open_tasks or [],
        "watchlist_items": watchlist or [],
    }


# ---------------------------------------------------------------------------
# score_customer — individual signals
# ---------------------------------------------------------------------------

def test_score_overdue_task(nba):
    rel = _rel_ctx(overdue=[{"title": "Call client", "days_overdue": 10}])
    result = nba.score_customer(_customer(), rel, {})
    assert "OVERDUE_TASK" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["OVERDUE_TASK"]


def test_score_two_overdue_tasks_capped_at_two(nba):
    overdue = [
        {"title": "Task A", "days_overdue": 5},
        {"title": "Task B", "days_overdue": 3},
        {"title": "Task C", "days_overdue": 1},
    ]
    result = nba.score_customer(_customer(), _rel_ctx(overdue=overdue), {})
    assert result["score"] == SIGNAL_SCORES["OVERDUE_TASK"] * 2


def test_score_upcoming_review_within_7_days(nba):
    review_date = (date.today() + timedelta(days=3)).isoformat()
    customer = _customer(next_review=review_date)
    result = nba.score_customer(customer, _rel_ctx(), {})
    assert "UPCOMING_REVIEW" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["UPCOMING_REVIEW"]


def test_score_no_upcoming_review_when_past(nba):
    past = (date.today() - timedelta(days=1)).isoformat()
    customer = _customer(next_review=past)
    result = nba.score_customer(customer, _rel_ctx(), {})
    assert "UPCOMING_REVIEW" not in result["reason_codes"]


def test_score_no_upcoming_review_when_far_future(nba):
    far = (date.today() + timedelta(days=30)).isoformat()
    customer = _customer(next_review=far)
    result = nba.score_customer(customer, _rel_ctx(), {})
    assert "UPCOMING_REVIEW" not in result["reason_codes"]


def test_score_idle_casa(nba):
    portfolio_ctx = {"liquidity": {"total_deployable_pct": 10.0, "holdings": []}}
    result = nba.score_customer(_customer(), _rel_ctx(), portfolio_ctx)
    assert "IDLE_CASA" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["IDLE_CASA"]


def test_score_no_idle_casa_below_threshold(nba):
    portfolio_ctx = {"liquidity": {"total_deployable_pct": 3.0, "holdings": []}}
    result = nba.score_customer(_customer(), _rel_ctx(), portfolio_ctx)
    assert "IDLE_CASA" not in result["reason_codes"]


def test_score_stale_contact(nba):
    rel = _rel_ctx(days_since=35)
    result = nba.score_customer(_customer(), rel, {})
    assert "NO_RECENT_CONTACT" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["NO_RECENT_CONTACT"]


def test_score_no_stale_contact_within_threshold(nba):
    rel = _rel_ctx(days_since=10)
    result = nba.score_customer(_customer(), rel, {})
    assert "NO_RECENT_CONTACT" not in result["reason_codes"]


def test_score_open_task(nba):
    tasks = [{"title": "Send report", "is_overdue": False}]
    result = nba.score_customer(_customer(), _rel_ctx(open_tasks=tasks), {})
    assert "OPEN_TASK" in result["reason_codes"]


def test_score_concentration_risk_in_task_title(nba):
    tasks = [{"title": "Review tech concentration risk", "is_overdue": False}]
    result = nba.score_customer(_customer(), _rel_ctx(open_tasks=tasks), {})
    assert "CONCENTRATION_RISK" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["CONCENTRATION_RISK"]


def test_score_concentration_risk_only_counted_once(nba):
    tasks = [
        {"title": "Review concentration", "is_overdue": False},
        {"title": "Another concentration task", "is_overdue": False},
    ]
    result = nba.score_customer(_customer(), _rel_ctx(open_tasks=tasks), {})
    assert result["reason_codes"].count("CONCENTRATION_RISK") == 1


def test_score_open_watchlist_items(nba):
    watchlist = [{"ticker": "NVDA"}, {"ticker": "TSM"}]
    result = nba.score_customer(_customer(), _rel_ctx(watchlist=watchlist), {})
    assert "OPEN_WATCHLIST" in result["reason_codes"]
    assert result["score"] >= SIGNAL_SCORES["OPEN_WATCHLIST"] * 2


# ---------------------------------------------------------------------------
# score_customer — confidence levels
# ---------------------------------------------------------------------------

def test_confidence_high(nba):
    overdue = [{"title": "T", "days_overdue": 5}] * 2
    rel = _rel_ctx(overdue=overdue, days_since=40)
    result = nba.score_customer(_customer(), rel, {})
    assert result["confidence"] == "high"


def test_confidence_medium(nba):
    # One overdue task = OVERDUE_TASK score (30) — 25 <= 30 < 50 → medium
    rel = _rel_ctx(overdue=[{"title": "T", "days_overdue": 5}])
    result = nba.score_customer(_customer(), rel, {})
    assert result["confidence"] == "medium"


def test_confidence_low_no_signals(nba):
    result = nba.score_customer(_customer(), _rel_ctx(), {})
    assert result["confidence"] == "low"
    assert result["score"] == 0


# ---------------------------------------------------------------------------
# score_all_customers
# ---------------------------------------------------------------------------

def test_score_all_customers_returns_at_most_5(nba):
    customers = [
        {"customer": _customer(cid=f"C{i:03d}"), "relationship_ctx": _rel_ctx(), "portfolio_ctx": {}}
        for i in range(8)
    ]
    result = nba.score_all_customers(customers)
    assert len(result) <= 5


def test_score_all_customers_sorted_descending(nba):
    customers = [
        {"customer": _customer("C001"), "relationship_ctx": _rel_ctx(days_since=40), "portfolio_ctx": {}},
        {"customer": _customer("C002"), "relationship_ctx": _rel_ctx(overdue=[{"title": "T", "days_overdue": 10}]), "portfolio_ctx": {}},
        {"customer": _customer("C003"), "relationship_ctx": _rel_ctx(), "portfolio_ctx": {}},
    ]
    result = nba.score_all_customers(customers)
    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True)


def test_score_all_customers_includes_metadata(nba):
    customers = [
        {"customer": _customer("C001"), "relationship_ctx": _rel_ctx(), "portfolio_ctx": {}}
    ]
    result = nba.score_all_customers(customers)
    assert len(result) == 1
    assert "score" in result[0]
    assert "reason_codes" in result[0]
    assert "confidence" in result[0]
    assert "client_name" in result[0]
