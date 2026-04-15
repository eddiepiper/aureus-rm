"""Unit tests for ChatRouter natural-language resolution (V5.1)."""
import pytest
from services.chat_router import ChatRouter, _extract_response_status


@pytest.fixture
def router():
    return ChatRouter(relationship_memory=None)


# ---------------------------------------------------------------------------
# Intent detection — V2
# ---------------------------------------------------------------------------

def test_client_review_resolves(router):
    res = router.resolve("chat1", "review John Tan")
    assert res.ready
    assert res.command == "client-review"
    assert "John" in res.args and "Tan" in res.args


def test_meeting_pack_resolves(router):
    res = router.resolve("chat1", "meeting pack for Sarah Lim")
    assert res.ready
    assert res.command == "meeting-pack"


def test_next_best_action_resolves(router):
    res = router.resolve("chat1", "what should I do for John Tan")
    assert res.ready
    assert res.command == "next-best-action"


# ---------------------------------------------------------------------------
# Intent detection — V5.1
# ---------------------------------------------------------------------------

def test_relationship_status_resolves(router):
    res = router.resolve("chat1", "relationship status for John Tan")
    assert res.ready
    assert res.command == "relationship-status"


def test_overdue_followups_resolves(router):
    res = router.resolve("chat1", "anything overdue for John Tan")
    assert res.ready
    assert res.command == "overdue-followups"


def test_attention_list_no_args(router):
    res = router.resolve("chat1", "who needs attention today")
    assert res.ready
    assert res.command == "attention-list"
    assert res.args == []


def test_morning_rm_brief_no_args(router):
    res = router.resolve("chat1", "what should I focus on today")
    assert res.ready
    assert res.command == "morning-rm-brief"
    assert res.args == []


# ---------------------------------------------------------------------------
# log_response natural language path (Critical fix #2)
# ---------------------------------------------------------------------------

def test_log_response_extracts_interested(router):
    res = router.resolve("chat1", "log response John Tan interested NVDA")
    assert res.ready
    assert res.command == "log-response"
    assert "interested" in res.args


def test_log_response_extracts_declined(router):
    res = router.resolve("chat1", "client said declined")
    # No client name supplied, should ask for one
    assert not res.ready
    assert res.reply is not None


def test_log_response_with_client_and_status(router):
    res = router.resolve("chat1", "client said John Tan declined")
    assert res.ready
    assert res.command == "log-response"
    assert "declined" in res.args


def test_log_response_missing_client_asks_question(router):
    res = router.resolve("chat1", "log response interested")
    assert not res.ready
    assert res.reply is not None


# ---------------------------------------------------------------------------
# _extract_response_status helper
# ---------------------------------------------------------------------------

def test_extract_interested():
    assert _extract_response_status("client is interested in NVDA") == "interested"


def test_extract_declined():
    assert _extract_response_status("client declined the recommendation") == "declined"


def test_extract_neutral():
    assert _extract_response_status("client seems neutral on this") == "neutral"


def test_extract_pending():
    assert _extract_response_status("status is pending") == "pending"


def test_extract_none_when_no_match():
    assert _extract_response_status("client called about something") is None


# ---------------------------------------------------------------------------
# Unknown intent + help
# ---------------------------------------------------------------------------

def test_unknown_intent_returns_reply(router):
    res = router.resolve("chat1", "hello there random text xyz")
    assert not res.ready
    assert res.reply is not None


def test_help_returns_reply(router):
    res = router.resolve("chat1", "help")
    assert not res.ready
    assert res.reply is not None
    assert "Aureus" in res.reply
