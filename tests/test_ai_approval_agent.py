"""
tests/test_ai_approval_agent.py

Unit tests for the V7 AIApprovalAgent deterministic assessment engine (assess()).

Design notes:
  - assess() is Claude-free — AIApprovalAgent(claude_service=None) is sufficient.
  - Criterion keys: "income" | "net_personal_assets" | "financial_assets".
    Any other value (including None) returns STATUS_PENDING_INFO.
  - Source control: source_is_internal=True bypasses evidence checks.
    External values without evidence_type + valid evidence_date are excluded.
  - Result: AIDecisionResult. Relevant fields: pass_result, assessment_status,
    confidence_level, recognised_amount_sgd, threshold_sgd,
    inconsistency_flags, missing_fields, manual_review_required.
  - Multi-path evaluation ("best", "4") is not supported.
    The engine assesses only the RM-selected criterion.
"""

import pytest

from services.ai_approval_agent import (
    AIApprovalAgent,
    AIDecisionResult,
    normalize_criteria,
    INCOME_THRESHOLD,
    NET_PERSONAL_ASSETS_THRESHOLD,
    FINANCIAL_ASSETS_THRESHOLD,
    STATUS_ELIGIBLE,
    STATUS_NOT_ELIGIBLE,
    STATUS_PENDING_INFO,
    STATUS_MANUAL_REVIEW,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent():
    """AIApprovalAgent without Claude service — assess() is Claude-free."""
    return AIApprovalAgent(claude_service=None)


def _income_data(**overrides):
    """Bank-held income data (source_is_internal=True) with all required fields."""
    base = {
        "annual_income": 400_000,
        "income_currency": "SGD",
        "income_period_start": "2025-04-01",
        "income_period_end": "2026-03-31",
        "source_is_internal": True,
    }
    base.update(overrides)
    return base


def _npa_data(**overrides):
    """Bank-held NPA data that qualifies cleanly using explicit NPA fields.

    Primary residence: FMV 3M - loan 500k = 2.5M equity, capped at 1M.
    Other assets: other_personal 600k + fin_for_npa 800k = 1.4M.
    recognised_npa = 600k + 800k + 1M = 2.4M — comfortably above 2M threshold.
    (2.1M would be borderline and trigger manual_review; 2.4M avoids this.)
    """
    base = {
        "primary_residence_fmv": 3_000_000,
        "primary_residence_secured_loan": 500_000,
        "ownership_share_pct": 1.0,
        "property_valuation_date": "2026-01-01",
        "other_personal_assets_value": 600_000,
        "financial_assets_for_npa_value": 800_000,
        "other_personal_liabilities_value": 0,
        "source_is_internal": True,
    }
    base.update(overrides)
    return base


def _nfa_data(**overrides):
    """Bank-held NFA data that qualifies cleanly.

    component_sum = 500k + 600k = 1.1M > SGD 1,000,000 threshold.
    """
    base = {
        "cash_holdings": 500_000,
        "investment_holdings": 600_000,
        "source_is_internal": True,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Scenario 1: Income-based eligibility
# ---------------------------------------------------------------------------

class TestIncomeEligibility:
    def test_qualifies_clearly(self, agent):
        data = _income_data(annual_income=400_000)
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True
        assert result.assessment_status == STATUS_ELIGIBLE
        assert result.selected_criterion == "income"
        assert result.recognised_amount_sgd == 400_000
        assert result.threshold_sgd == INCOME_THRESHOLD
        assert result.confidence_level == CONFIDENCE_HIGH
        assert result.missing_fields == []
        assert result.inconsistency_flags == []

    def test_does_not_qualify_below_threshold(self, agent):
        data = _income_data(annual_income=250_000)
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is False
        assert result.assessment_status == STATUS_NOT_ELIGIBLE
        assert result.confidence_level == CONFIDENCE_LOW

    def test_borderline_value_triggers_manual_review(self, agent):
        """Value within 10% above threshold → manual_review, confidence capped at Medium."""
        borderline = int(INCOME_THRESHOLD * 1.05)  # 315,000
        data = _income_data(annual_income=borderline)
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True
        assert result.assessment_status == STATUS_MANUAL_REVIEW
        assert result.confidence_level == CONFIDENCE_MEDIUM
        assert result.manual_review_required is True
        assert any("borderline" in r.lower() for r in result.manual_review_reasons)

    def test_missing_income_field_returns_pending_info(self, agent):
        data = {"income_currency": "SGD", "source_is_internal": True}
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO
        assert "annual_income" in result.missing_fields
        assert result.confidence_level == CONFIDENCE_LOW

    def test_missing_income_period_triggers_manual_review(self, agent):
        """income_period_start/end absent → manual_review even when income qualifies."""
        data = {
            "annual_income": 500_000,
            "income_currency": "SGD",
            "source_is_internal": True,
        }
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True
        assert result.assessment_status == STATUS_MANUAL_REVIEW
        assert any("income_period" in f for f in result.missing_fields)


# ---------------------------------------------------------------------------
# Scenario 2: Net Personal Assets eligibility
# ---------------------------------------------------------------------------

class TestNetPersonalAssetsEligibility:
    def test_qualifies_clearly(self, agent):
        data = _npa_data()
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert result.assessment_status == STATUS_ELIGIBLE
        assert result.selected_criterion == "net_personal_assets"
        assert result.recognised_amount_sgd == pytest.approx(2_400_000)
        assert result.threshold_sgd == NET_PERSONAL_ASSETS_THRESHOLD
        assert result.confidence_level == CONFIDENCE_HIGH
        assert result.inconsistency_flags == []

    def test_does_not_qualify_below_threshold(self, agent):
        data = _npa_data(
            primary_residence_fmv=500_000,
            primary_residence_secured_loan=0,
            other_personal_assets_value=0,
            financial_assets_for_npa_value=0,
        )
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_NOT_ELIGIBLE

    def test_missing_all_npa_fields_returns_pending_info(self, agent):
        result = agent.assess(
            {}, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO
        assert result.missing_fields

    def test_legacy_net_assets_fallback_with_flag(self, agent):
        """Legacy net_assets used when new fields absent — expect manual_review flag."""
        data = {"net_assets": 2_500_000, "source_is_internal": True}
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert any("legacy" in f.lower() for f in result.inconsistency_flags)

    def test_legacy_total_assets_fallback(self, agent):
        """total_assets − total_liabilities used as fallback when new fields absent."""
        data = {
            "total_assets": 3_000_000,
            "total_liabilities": 500_000,
            "source_is_internal": True,
        }
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert result.recognised_amount_sgd == pytest.approx(2_500_000)
        assert any("legacy" in f.lower() for f in result.inconsistency_flags)

    def test_joint_account_without_ownership_share_adds_missing(self, agent):
        """joint_account_flag=True without ownership_share_pct → missing field."""
        data = _npa_data(joint_account_flag=True, ownership_share_pct=None)
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert any("ownership_share_pct" in f for f in result.missing_fields)


# ---------------------------------------------------------------------------
# Scenario 3: Financial assets eligibility (John Tan default path)
# ---------------------------------------------------------------------------

class TestFinancialAssetsEligibility:
    def test_john_tan_mock_qualifies(self, agent):
        from services.mock_data import MOCK_AI_ASSESSMENTS

        data = MOCK_AI_ASSESSMENTS[0]
        result = agent.assess(
            data, criterion="financial_assets", customer_name="John Tan"
        )

        assert result.pass_result is True
        assert result.assessment_status == STATUS_ELIGIBLE
        assert result.selected_criterion == "financial_assets"
        assert result.recognised_amount_sgd == pytest.approx(1_500_000)
        assert result.threshold_sgd == FINANCIAL_ASSETS_THRESHOLD
        assert result.confidence_level == CONFIDENCE_HIGH
        assert result.inconsistency_flags == []

    def test_qualifies_with_component_breakdown(self, agent):
        data = _nfa_data()
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert result.assessment_status == STATUS_ELIGIBLE
        assert result.recognised_amount_sgd == pytest.approx(1_100_000)
        assert result.confidence_level == CONFIDENCE_HIGH

    def test_does_not_qualify_below_threshold(self, agent):
        data = _nfa_data(cash_holdings=200_000, investment_holdings=300_000)
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_NOT_ELIGIBLE

    def test_missing_financial_assets_data_returns_pending_info(self, agent):
        result = agent.assess(
            {}, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO
        assert result.missing_fields

    def test_cpfis_included_in_recognised_nfa(self, agent):
        data = _nfa_data(
            cash_holdings=400_000,
            investment_holdings=500_000,
            cpf_investment_amount=200_000,
        )
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert result.recognised_amount_sgd == pytest.approx(1_100_000)

    def test_margin_loan_deducted_from_nfa(self, agent):
        data = _nfa_data(
            cash_holdings=500_000,
            investment_holdings=800_000,
            margin_loan_balance=200_000,
        )
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is True
        assert result.recognised_amount_sgd == pytest.approx(1_100_000)


# ---------------------------------------------------------------------------
# Scenario 4: Missing data
# ---------------------------------------------------------------------------

class TestMissingData:
    def test_empty_income_data_returns_pending_info(self, agent):
        result = agent.assess({}, criterion="income", customer_name="Test Client")

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO
        assert result.confidence_level == CONFIDENCE_LOW
        assert result.missing_fields

    def test_empty_npa_data_returns_pending_info(self, agent):
        result = agent.assess(
            {}, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO

    def test_empty_nfa_data_returns_pending_info(self, agent):
        result = agent.assess(
            {}, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO


# ---------------------------------------------------------------------------
# Scenario 5: Conflicting / inconsistent data
# ---------------------------------------------------------------------------

class TestInconsistentData:
    def test_financial_assets_component_sum_mismatch(self, agent):
        """total_financial_assets declared but differs from component breakdown."""
        data = {
            "total_financial_assets": 2_000_000,
            "cash_holdings": 300_000,
            "investment_holdings": 400_000,
            "cpf_investment_amount": 100_000,
            "source_is_internal": True,
        }
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert any("differs from" in f for f in result.inconsistency_flags)

    def test_negative_recognised_nfa_flagged(self, agent):
        """Liabilities exceed assets → negative recognised_nfa → inconsistency flag."""
        data = {
            "cash_holdings": 100_000,
            "margin_loan_balance": 300_000,
            "source_is_internal": True,
        }
        result = agent.assess(
            data, criterion="financial_assets", customer_name="Test Client"
        )

        assert result.pass_result is False
        assert any("negative" in f.lower() for f in result.inconsistency_flags)

    def test_stale_income_evidence_triggers_manual_review(self, agent):
        """Evidence older than the type's max age → manual_review."""
        data = _income_data(
            evidence_type="income_statement",
            evidence_date="2025-01-01",  # > 60 days before 2026-04-17
            source_is_internal=False,
        )
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is False

    def test_stale_property_valuation_triggers_manual_review(self, agent):
        """Property valuation > 365 days old → manual_review; reason recorded."""
        data = _npa_data(property_valuation_date="2024-01-01")
        result = agent.assess(
            data, criterion="net_personal_assets", customer_name="Test Client"
        )

        assert result.manual_review_required is True
        # Stale reason surfaces in manual_review_reasons; the raw flag notes "days old"
        assert any(
            "stale" in r.lower() or "days old" in r.lower()
            for r in result.manual_review_reasons + result.inconsistency_flags
        )


# ---------------------------------------------------------------------------
# Currency handling (income criterion)
# ---------------------------------------------------------------------------

class TestCurrencyHandling:
    def test_non_sgd_without_fx_rate_blocks_assessment(self, agent):
        """Non-SGD income without fx_rate_used → income excluded → pending_info."""
        data = _income_data(income_currency="USD", fx_rate_used=None)
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is False
        assert any(
            "cannot normalise" in f.lower() or "fx_rate_used" in f.lower()
            for f in result.inconsistency_flags
        )

    def test_non_sgd_with_fx_rate_converts_and_qualifies(self, agent):
        """USD income × fx_rate ≥ SGD 300,000 → eligible."""
        data = _income_data(
            annual_income=300_000,
            income_currency="USD",
            fx_rate_used=1.35,
            fx_rate_date="2026-04-01",
        )
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True
        assert result.recognised_amount_sgd == pytest.approx(405_000)

    def test_sgd_income_passes_through_normally(self, agent):
        data = _income_data(income_currency="SGD")
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True

    def test_missing_currency_defaults_to_sgd(self, agent):
        """No income_currency → treated as SGD, not blocked."""
        data = {k: v for k, v in _income_data().items() if k != "income_currency"}
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True


# ---------------------------------------------------------------------------
# Invalid / unrecognised criterion
# ---------------------------------------------------------------------------

class TestInvalidCriterion:
    @pytest.mark.parametrize("criterion", [None, "best", "4", "evaluate_all", "unknown"])
    def test_unrecognised_criterion_returns_pending_info(self, agent, criterion):
        """Any criterion not in {income, net_personal_assets, financial_assets} → pending_info."""
        result = agent.assess(
            _income_data(), criterion=criterion, customer_name="Test Client"
        )

        assert result.pass_result is False
        assert result.assessment_status == STATUS_PENDING_INFO
        assert result.missing_fields  # explains the unrecognised criterion

    def test_pending_info_checker_recommendation_requests_resubmit(self, agent):
        result = agent.assess({}, criterion="income", customer_name="Test Client")

        assert result.checker_recommendation
        assert result.checker_status == "pending_review"


# ---------------------------------------------------------------------------
# Source control — external values without evidence are excluded
# ---------------------------------------------------------------------------

class TestSourceControl:
    def test_external_income_without_evidence_excluded(self, agent):
        """External income (source_is_internal=False) without evidence_type → excluded."""
        data = {
            "annual_income": 400_000,
            "income_currency": "SGD",
            "income_period_start": "2025-04-01",
            "income_period_end": "2026-03-31",
            "source_is_internal": False,
            # no evidence_type or evidence_date
        }
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is False
        assert any(
            "excluded" in f.lower() or "evidence" in f.lower()
            for f in result.inconsistency_flags
        )

    def test_external_income_with_valid_evidence_passes(self, agent):
        """External income with valid evidence_type + non-stale evidence_date → accepted."""
        data = {
            "annual_income": 400_000,
            "income_currency": "SGD",
            "income_period_start": "2025-04-01",
            "income_period_end": "2026-03-31",
            "source_is_internal": False,
            "evidence_type": "income_statement",
            "evidence_date": "2026-03-15",  # within 60 days of 2026-04-17
        }
        result = agent.assess(data, criterion="income", customer_name="Test Client")

        assert result.pass_result is True


# ---------------------------------------------------------------------------
# normalize_criteria
# ---------------------------------------------------------------------------

class TestNormalizeCriteria:
    @pytest.mark.parametrize("raw,expected", [
        # Numeric shortcuts
        ("1", "income"),
        ("2", "net_personal_assets"),
        ("3", "financial_assets"),
        # Income aliases
        ("income", "income"),
        ("Income", "income"),
        ("INCOME", "income"),
        ("annual income", "income"),
        ("salary", "income"),
        # Net personal assets aliases
        ("net assets", "net_personal_assets"),
        ("Net Assets", "net_personal_assets"),
        ("net personal assets", "net_personal_assets"),
        ("net_personal_assets", "net_personal_assets"),
        # Financial assets aliases
        ("financial assets", "financial_assets"),
        ("Financial Assets", "financial_assets"),
        ("financial_assets", "financial_assets"),
        ("investments", "financial_assets"),
    ])
    def test_known_aliases(self, raw, expected):
        assert normalize_criteria(raw) == expected

    @pytest.mark.parametrize("raw", [
        # "4" / "best" / "evaluate all" are not supported
        "4", "best", "evaluate all", "all", "not sure",
        # Completely unknown
        "something random", "xyz",
    ])
    def test_unsupported_or_unknown_returns_none(self, raw):
        assert normalize_criteria(raw) is None

    def test_empty_string_returns_none(self):
        assert normalize_criteria("") is None

    def test_none_returns_none(self):
        assert normalize_criteria(None) is None

    def test_whitespace_stripped(self):
        assert normalize_criteria("  1  ") == "income"
        assert normalize_criteria("  net assets  ") == "net_personal_assets"
        assert normalize_criteria("  financial assets  ") == "financial_assets"


# ---------------------------------------------------------------------------
# AIDecisionResult structure
# ---------------------------------------------------------------------------

class TestDecisionResultStructure:
    def test_result_is_dataclass_instance(self, agent):
        result = agent.assess(_income_data(), criterion="income", customer_name="T")
        assert isinstance(result, AIDecisionResult)

    def test_result_preserves_customer_metadata(self, agent):
        result = agent.assess(
            _income_data(),
            criterion="income",
            customer_name="John Tan",
            customer_id="CUST001",
        )

        assert result.customer_name == "John Tan"
        assert result.customer_id == "CUST001"

    def test_checker_status_defaults_to_pending_review(self, agent):
        result = agent.assess(_income_data(), criterion="income", customer_name="T")
        assert result.checker_status == "pending_review"

    def test_eligible_result_has_checker_recommendation(self, agent):
        result = agent.assess(_income_data(), criterion="income", customer_name="T")
        assert result.checker_recommendation
        assert len(result.checker_recommendation) > 0

    def test_not_eligible_result_has_checker_recommendation(self, agent):
        result = agent.assess(
            _income_data(annual_income=100_000),
            criterion="income",
            customer_name="T",
        )
        assert result.checker_recommendation
