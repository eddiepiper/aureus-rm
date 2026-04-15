"""Unit tests for WritebackService utilities (V5.1)."""
import pytest
from services.writeback_service import build_duplicate_key


def test_duplicate_key_basic():
    key = build_duplicate_key("CUST001", "followup", "NVDA", "idea_generation")
    assert key == "CUST001:followup:NVDA:idea_generation"


def test_duplicate_key_no_ticker():
    key = build_duplicate_key("CUST001", "review", None, "meeting_pack")
    assert key == "CUST001:review:none:meeting_pack"


def test_duplicate_key_normalizes_category_spaces():
    key = build_duplicate_key("CUST001", "follow up", None, "next_best_action")
    assert key == "CUST001:follow_up:none:next_best_action"


def test_duplicate_key_normalizes_category_hyphens():
    key = build_duplicate_key("CUST001", "follow-up", None, "next_best_action")
    assert key == "CUST001:follow_up:none:next_best_action"


def test_duplicate_key_normalizes_customer_id_lowercase():
    key1 = build_duplicate_key("cust001", "review", None, "meeting_pack")
    key2 = build_duplicate_key("CUST001", "review", None, "meeting_pack")
    assert key1 == key2


def test_duplicate_key_normalizes_customer_id_mixed_case():
    key1 = build_duplicate_key("Cust001", "review", None, "meeting_pack")
    key2 = build_duplicate_key("CUST001", "review", None, "meeting_pack")
    assert key1 == key2


def test_duplicate_key_normalizes_ticker_lowercase():
    key1 = build_duplicate_key("CUST001", "followup", "nvda", "idea_generation")
    key2 = build_duplicate_key("CUST001", "followup", "NVDA", "idea_generation")
    assert key1 == key2


def test_duplicate_key_strips_whitespace():
    key = build_duplicate_key("  CUST001  ", "  followup  ", "  NVDA  ", "  idea_generation  ")
    assert key == "CUST001:followup:NVDA:idea_generation"


def test_duplicate_key_format_has_four_parts():
    key = build_duplicate_key("CUST001", "review", "DBS", "meeting_pack")
    parts = key.split(":")
    assert len(parts) == 4
