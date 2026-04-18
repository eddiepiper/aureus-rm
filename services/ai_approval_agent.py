"""
services/ai_approval_agent.py

Singapore Accredited Investor (AI) eligibility assessment engine for individual customers.

Three-layer design:
  Layer 1 — normalize_assessment_input()
              Pure functions: type coercion, null handling, source classification.
  Layer 2 — _evaluate_income() / _evaluate_net_personal_assets() / _evaluate_financial_assets()
              Deterministic criterion-specific decision engines. No Claude.
  Layer 3 — AIApprovalAgent.generate()
              Claude drafts a memo from the structured AIDecisionResult.
              Claude cannot change the decision — it only renders prose.

Locked business rules:
  - RM selects exactly ONE criterion. The engine assesses only that criterion.
  - If the selected criterion fails, the result is not_eligible for that criterion.
  - No auto-switching to an alternative criterion.
  - Borderline pass (within 10% above threshold) → manual_review, confidence capped at Medium.
  - External manually-keyed values without acceptable evidence are excluded from recognised amount.
  - Internal bank-held values (source_is_internal = True) may support pass even if manually keyed.
  - CPFIS included in NFA; raw CPF balances are explicitly excluded.
  - DPT/stablecoin handling is entirely absent from this engine.
  - Joint account is flag-only in this version — no separate qualification path.
  - Checker confirms or rejects; this engine produces a draft only.

Not user-facing. All output is routed through AureusOrchestrator → Aureus.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Policy configuration
# All thresholds and recency windows are centralised here for auditability.
# ---------------------------------------------------------------------------

AI_ASSESSMENT_POLICY: dict = {
    "thresholds": {
        "income":               300_000,
        "net_personal_assets":  2_000_000,
        "financial_assets":     1_000_000,
    },
    # Borderline band: result within this % above threshold → manual_review
    "borderline_pct": 0.10,
    # Maximum evidence age (in days) per evidence type.
    # None = supplementary only — recency is not enforced but the field is referenced.
    "evidence_max_age_days": {
        "income_statement":                 60,
        "employer_letter":                  60,
        "external_investment_statement":    60,
        "letter_of_financial_standing":     90,
        "property_valuation":               365,
        "noa":                              None,   # supplementary, not sufficient alone
    },
}

# Module-level threshold constants (for direct import in tests / external callers)
INCOME_THRESHOLD:               int = AI_ASSESSMENT_POLICY["thresholds"]["income"]
NET_PERSONAL_ASSETS_THRESHOLD:  int = AI_ASSESSMENT_POLICY["thresholds"]["net_personal_assets"]
FINANCIAL_ASSETS_THRESHOLD:     int = AI_ASSESSMENT_POLICY["thresholds"]["financial_assets"]
BORDERLINE_PCT:                float = AI_ASSESSMENT_POLICY["borderline_pct"]

# ---------------------------------------------------------------------------
# Assessment status and confidence level constants
# ---------------------------------------------------------------------------

STATUS_ELIGIBLE         = "eligible"
STATUS_NOT_ELIGIBLE     = "not_eligible"
STATUS_PENDING_INFO     = "pending_info"
STATUS_MANUAL_REVIEW    = "manual_review"

CONFIDENCE_HIGH     = "High"
CONFIDENCE_MEDIUM   = "Medium"
CONFIDENCE_LOW      = "Low"

# ---------------------------------------------------------------------------
# Criteria normalisation
# "best" / "4" / "evaluate all" are intentionally absent — the engine
# assesses only the RM-selected criterion.
# ---------------------------------------------------------------------------

_CRITERIA_ALIASES: dict[str, str] = {
    # Number shortcuts — only 1 / 2 / 3
    "1": "income",
    "2": "net_personal_assets",
    "3": "financial_assets",
    # Income aliases
    "income":               "income",
    "annual income":        "income",
    "income based":         "income",
    "income basis":         "income",
    "salary":               "income",
    "employment income":    "income",
    # Net personal assets aliases
    "net personal assets":  "net_personal_assets",
    "net assets":           "net_personal_assets",
    "net asset":            "net_personal_assets",
    "total net assets":     "net_personal_assets",
    "net_personal_assets":  "net_personal_assets",
    # Financial assets aliases
    "financial assets":         "financial_assets",
    "financial asset":          "financial_assets",
    "total financial assets":   "financial_assets",
    "net financial assets":     "financial_assets",
    "investments":              "financial_assets",
    "financial_assets":         "financial_assets",
}


def normalize_criteria(raw: str) -> Optional[str]:
    """
    Normalise RM input to an internal criterion identifier.
    Returns: "income" | "net_personal_assets" | "financial_assets" | None

    Option 4 / "best" / "evaluate all" are not accepted — the RM must
    select a specific criterion. Unknown input returns None.
    """
    if not raw:
        return None
    return _CRITERIA_ALIASES.get(raw.strip().lower())


# ---------------------------------------------------------------------------
# Decision result (structured output — the required decision object)
# ---------------------------------------------------------------------------

@dataclass
class AIDecisionResult:
    """
    Structured output of the AI eligibility assessment engine.

    This object is the canonical source of truth for the assessment.
    Claude only renders the memo_text from this object — it cannot modify
    pass_result, assessment_status, recognised_amount_sgd, or any logic field.
    """
    customer_id:            str
    customer_name:          str
    selected_criterion:     str             # "income" | "net_personal_assets" | "financial_assets"
    recognised_amount_sgd:  Optional[float]
    threshold_sgd:          float
    pass_result:            bool
    assessment_status:      str             # STATUS_* constant
    confidence_level:       str             # CONFIDENCE_* constant
    missing_fields:         list = field(default_factory=list)
    inconsistency_flags:    list = field(default_factory=list)
    manual_review_required: bool = False
    manual_review_reasons:  list = field(default_factory=list)
    joint_account_flag:     bool = False
    joint_account_note:     str = ""
    checker_status:         str = "pending_review"
    checker_recommendation: str = ""
    evidence_summary:       str = ""
    computation_notes:      list = field(default_factory=list)   # audit trail, not shown to RM


# ---------------------------------------------------------------------------
# Layer 1 — Input normalisation
# ---------------------------------------------------------------------------

def _to_float(value) -> Optional[float]:
    """Safely coerce a Sheets value (str, int, float, empty) to float or None."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _to_bool(value) -> bool:
    """Coerce a Sheets value to bool. Defaults to False if absent or unrecognised."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "y")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _parse_date(value) -> Optional[date_cls]:
    """Parse an ISO-format date string (YYYY-MM-DD) or return None."""
    if not value:
        return None
    try:
        return date_cls.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None


def normalize_assessment_input(raw: dict) -> dict:
    """
    Layer 1 normalisation: converts raw Sheets/mock dict to clean typed values.

    - Numeric fields → float or None
    - Boolean fields → bool (default False)
    - String fields → stripped str or None
    - ownership_share_pct: if provided as e.g. 50 (meaning 50%), converted to 0.5
    """
    normalized: dict = dict(raw)  # shallow copy

    _NUMERIC_FIELDS = (
        "annual_income", "salary_ytd", "bonus_ytd", "latest_noa_amount",
        "fx_rate_used",
        # NPA fields
        "total_assets", "total_liabilities", "net_assets",
        "primary_residence_fmv", "primary_residence_secured_loan", "ownership_share_pct",
        "other_personal_assets_value", "other_real_estate_value", "other_real_estate_secured_loans",
        "financial_assets_for_npa_value", "insurance_surrender_value",
        "business_interest_value", "other_personal_liabilities_value",
        # Deprecated legacy fields (backward-read only)
        "property_value", "mortgage_liability", "financial_assets_networth",
        # NFA fields
        "total_financial_assets", "cash_holdings", "investment_holdings",
        "cpf_investment_amount", "funds_under_management_value",
        "financial_assets_related_liabilities", "margin_loan_balance", "portfolio_credit_line_balance",
    )
    for f in _NUMERIC_FIELDS:
        if f in normalized:
            normalized[f] = _to_float(normalized.get(f))

    # ownership_share_pct: convert percentage notation (e.g. 50 → 0.5)
    pct = normalized.get("ownership_share_pct")
    if pct is not None and pct > 1.0:
        normalized["ownership_share_pct"] = pct / 100.0

    # Boolean fields
    normalized["source_is_internal"] = _to_bool(raw.get("source_is_internal"))
    normalized["joint_account_flag"]  = _to_bool(raw.get("joint_account_flag"))

    # String fields — strip whitespace, keep None if absent
    _STRING_FIELDS = (
        "income_currency", "evidence_type", "evidence_date",
        "income_period_start", "income_period_end", "fx_rate_date",
        "latest_noa_year", "statement_date", "valuation_date",
        "property_valuation_date", "data_source", "customer_id",
        "customer_name", "selected_criterion", "joint_account_note",
        "income_source", "employer_name", "income_year",
    )
    for f in _STRING_FIELDS:
        val = raw.get(f)
        normalized[f] = str(val).strip() if val is not None else None

    return normalized


# ---------------------------------------------------------------------------
# Layer 1 — Evidence and source helpers
# ---------------------------------------------------------------------------

def _get_evidence_max_age(evidence_type: str, policy: dict) -> Optional[int]:
    """
    Return the maximum allowed age (days) for an evidence type, or None
    if the type is supplementary / unknown.
    Uses case-insensitive, normalised partial matching.
    """
    if not evidence_type:
        return None
    et_key = evidence_type.strip().lower().replace(" ", "_").replace("-", "_")
    age_map = policy.get("evidence_max_age_days", {})
    if et_key in age_map:
        return age_map[et_key]
    # Partial match
    for key, val in age_map.items():
        if key in et_key or et_key in key:
            return val
    return None  # unknown type — no age limit enforced


def _check_evidence_recency(
    evidence_type: str,
    evidence_date: str,
    today: date_cls,
    policy: dict,
) -> tuple[bool, str]:
    """
    Returns (is_stale, reason).
    is_stale = True when evidence exceeds the maximum allowed age for its type.
    """
    if not evidence_type or not evidence_date:
        return False, ""
    ed = _parse_date(evidence_date)
    if ed is None:
        return True, f"Cannot parse evidence_date '{evidence_date}'"
    max_age = _get_evidence_max_age(evidence_type, policy)
    if max_age is None:
        return False, ""  # supplementary or unknown — not enforced
    days_old = (today - ed).days
    if days_old > max_age:
        return True, (
            f"{evidence_type} dated {evidence_date} is {days_old} days old "
            f"(limit {max_age} days for this evidence type)"
        )
    return False, ""


def _is_value_supported(
    source_is_internal: bool,
    evidence_type: str,
    evidence_date: str,
    today: date_cls,
    policy: dict,
) -> tuple[bool, str]:
    """
    Determine whether a value can support a pass result.

    Policy (locked):
    - source_is_internal = True  → always supported (bank-held, directly verifiable)
    - source_is_internal = False → requires evidence_type AND non-stale evidence_date
      If either is missing or stale, the value CANNOT support pass.
    """
    if source_is_internal:
        return True, ""

    if not evidence_type:
        return False, "External source: evidence_type not provided"

    if not evidence_date:
        return False, f"External source ({evidence_type}): evidence_date not provided"

    ed = _parse_date(evidence_date)
    if ed is None:
        return False, f"Cannot parse evidence_date '{evidence_date}'"

    max_age = _get_evidence_max_age(evidence_type, policy)
    if max_age is not None:
        days_old = (today - ed).days
        if days_old > max_age:
            return False, (
                f"Stale evidence: {evidence_type} dated {evidence_date} "
                f"is {days_old} days old (max {max_age} days)"
            )

    return True, ""


# ---------------------------------------------------------------------------
# Layer 2 — Deterministic criterion evaluators
# Each returns: (recognised_amount_or_None, missing_fields, flags, mr_reasons, notes)
# ---------------------------------------------------------------------------

def _evaluate_income(
    normalized: dict,
    policy: dict,
    today: date_cls,
) -> tuple[Optional[float], list, list, list, list]:
    """
    Income criterion evaluator.
    Pass if recognised_income_sgd >= SGD 300,000.

    Primary basis: income_period_start / income_period_end (preceding 12 months).
    NOA (latest_noa_year / latest_noa_amount) is supplementary only.
    External manual values without acceptable evidence are excluded.
    """
    missing: list   = []
    flags:   list   = []
    mr:      list   = []
    notes:   list   = []

    # --- Critical field: annual_income ---
    income = normalized.get("annual_income")
    if income is None:
        missing.append("annual_income")
        return None, missing, flags, mr, notes

    # --- FX normalization ---
    currency = str(normalized.get("income_currency") or "SGD").strip().upper()
    if currency and currency != "SGD":
        fx_rate = normalized.get("fx_rate_used")
        fx_date = normalized.get("fx_rate_date")
        if fx_rate is None:
            flags.append(
                f"income_currency is {currency} but fx_rate_used is missing — "
                "cannot normalise to SGD"
            )
            mr.append(
                f"Non-SGD income ({currency}) without FX rate — cannot finalise eligible result"
            )
            return None, missing, flags, mr, notes
        if fx_date is None:
            flags.append(f"fx_rate_date missing for {currency} income conversion — FX basis unverifiable")
            mr.append("FX rate date missing — FX basis cannot be verified")
        income_sgd = income * fx_rate
        notes.append(
            f"Income {income:,.0f} {currency} × {fx_rate} = SGD {income_sgd:,.0f} "
            f"(rate date: {fx_date or 'not provided'})"
        )
        income = income_sgd

    # --- Source control: external manual value gate ---
    source_is_internal = normalized.get("source_is_internal", False)
    evidence_type      = normalized.get("evidence_type") or ""
    evidence_date      = normalized.get("evidence_date") or ""

    supported, support_reason = _is_value_supported(
        source_is_internal, evidence_type, evidence_date, today, policy
    )
    if not supported:
        flags.append(f"Income value excluded — {support_reason}")
        mr.append(f"Income cannot support pass: {support_reason}")
        return None, missing, flags, mr, notes

    # --- Income period (primary 12-month basis) ---
    period_start = normalized.get("income_period_start")
    period_end   = normalized.get("income_period_end")
    if not period_start or not period_end:
        missing.append("income_period_start")
        missing.append("income_period_end")
        mr.append(
            "Preceding-12-month income period (income_period_start / income_period_end) "
            "not defined — primary income basis incomplete"
        )
    else:
        notes.append(f"Income period: {period_start} to {period_end}")
        ps = _parse_date(period_start)
        pe = _parse_date(period_end)
        if ps and pe:
            days = (pe - ps).days
            if days < 300 or days > 400:
                flags.append(
                    f"Income period ({period_start} to {period_end}) spans {days} days — "
                    "expected approximately 365 days for preceding-12-month basis"
                )
        else:
            flags.append(
                f"Cannot parse income_period_start '{period_start}' or income_period_end '{period_end}'"
            )

    # --- Evidence recency (stale core evidence → manual review) ---
    if evidence_date and evidence_type:
        stale, stale_reason = _check_evidence_recency(evidence_type, evidence_date, today, policy)
        if stale:
            flags.append(stale_reason)
            mr.append(f"Stale core evidence — {stale_reason}")

    # --- NOA supplementary reference ---
    noa_year = normalized.get("latest_noa_year")
    if noa_year:
        notes.append(f"NOA {noa_year} present as supplementary reference (not primary basis)")

    return income, missing, flags, mr, notes


def _evaluate_net_personal_assets(
    normalized: dict,
    policy: dict,
    today: date_cls,
) -> tuple[Optional[float], list, list, list, list]:
    """
    Net Personal Assets (NPA) criterion evaluator.
    Pass if recognised_npa_sgd > SGD 2,000,000.

    Formula (explicit fields preferred; legacy fallback documented):
      primary_residence_net_equity = max(0, (primary_residence_fmv × ownership_share_pct)
                                            − (primary_residence_secured_loan × ownership_share_pct))
      recognised_primary_residence  = min(primary_residence_net_equity, 1,000,000)
      recognised_npa =
          other_personal_assets_value
          + other_real_estate_equity
          + financial_assets_for_npa_value
          + insurance_surrender_value
          + business_interest_value
          + recognised_primary_residence
          − other_personal_liabilities_value

    Ownership share is applied to primary residence and other real estate.
    Gross property value is never used directly.
    External manually-keyed values without acceptable evidence are excluded.
    """
    missing: list   = []
    flags:   list   = []
    mr:      list   = []
    notes:   list   = []

    source_is_internal = normalized.get("source_is_internal", False)
    evidence_type      = normalized.get("evidence_type") or ""
    evidence_date      = normalized.get("evidence_date") or ""

    supported, support_reason = _is_value_supported(
        source_is_internal, evidence_type, evidence_date, today, policy
    )

    # --- Ownership share ---
    joint_flag     = normalized.get("joint_account_flag", False)
    ownership_pct  = normalized.get("ownership_share_pct")
    if joint_flag and ownership_pct is None:
        missing.append("ownership_share_pct (required when joint_account_flag is true)")
        mr.append(
            "Joint account flagged but ownership_share_pct not provided — "
            "cannot apply correct ownership share"
        )
    if ownership_pct is None:
        ownership_pct = 1.0   # assume 100% if not stated and not joint

    # --- Primary residence ---
    pr_fmv  = normalized.get("primary_residence_fmv")
    pr_loan = normalized.get("primary_residence_secured_loan") or 0.0

    # Backward-read legacy field if new field absent
    if pr_fmv is None:
        pr_fmv = normalized.get("property_value")
    if pr_loan == 0.0:
        pr_loan = normalized.get("mortgage_liability") or 0.0

    recognised_pr = 0.0
    if pr_fmv is not None:
        pv_date = normalized.get("property_valuation_date") or normalized.get("valuation_date")
        if pv_date:
            stale, stale_reason = _check_evidence_recency("property_valuation", pv_date, today, policy)
            if stale:
                flags.append(stale_reason)
                mr.append(f"Stale property valuation — {stale_reason}")
        else:
            flags.append(
                "property_valuation_date missing for primary residence — "
                "valuation recency cannot be confirmed"
            )
            mr.append("Primary residence valuation date not provided — manual review required")

        pr_equity = max(0.0, (pr_fmv * ownership_pct) - (pr_loan * ownership_pct))
        recognised_pr = min(pr_equity, 1_000_000.0)
        notes.append(
            f"Primary residence: FMV {pr_fmv:,.0f} × {ownership_pct:.0%} "
            f"− loan share {pr_loan * ownership_pct:,.0f} "
            f"= equity {pr_equity:,.0f} → capped at SGD 1,000,000 → {recognised_pr:,.0f}"
        )

    # --- Asset value helper (applies source control gate per value) ---
    def _asset(field_name: str, label: str) -> float:
        val = normalized.get(field_name) or 0.0
        if val > 0 and not supported:
            flags.append(
                f"{label} ({val:,.0f}) excluded — external manual value without "
                f"acceptable evidence: {support_reason}"
            )
            return 0.0
        return val

    other_personal  = _asset("other_personal_assets_value",  "other_personal_assets_value")
    ore_value       = normalized.get("other_real_estate_value") or 0.0
    ore_loans       = normalized.get("other_real_estate_secured_loans") or 0.0
    other_re_equity = 0.0
    if ore_value > 0:
        if not supported:
            flags.append(
                f"other_real_estate_value ({ore_value:,.0f}) excluded — "
                f"external manual value without acceptable evidence: {support_reason}"
            )
        else:
            other_re_equity = max(0.0, (ore_value - ore_loans) * ownership_pct)
            notes.append(
                f"Other real estate: ({ore_value:,.0f} − {ore_loans:,.0f}) "
                f"× {ownership_pct:.0%} = {other_re_equity:,.0f}"
            )

    fin_for_npa     = _asset("financial_assets_for_npa_value",  "financial_assets_for_npa_value")
    insurance_sv    = _asset("insurance_surrender_value",        "insurance_surrender_value")
    biz_interest    = _asset("business_interest_value",          "business_interest_value")
    other_liab      = normalized.get("other_personal_liabilities_value") or 0.0

    # --- Check if any explicit new-field values were populated ---
    total_new_fields = (
        other_personal + other_re_equity + fin_for_npa + insurance_sv + biz_interest
    )

    if total_new_fields == 0.0 and recognised_pr == 0.0:
        # Nothing in new fields — try legacy net_assets or total_assets - liabilities
        legacy_net    = normalized.get("net_assets")
        legacy_total  = normalized.get("total_assets")
        legacy_liab   = normalized.get("total_liabilities")

        if legacy_net is not None:
            if supported:
                recognised_npa = legacy_net
                flags.append(
                    "Using legacy net_assets field — new explicit NPA fields not populated. "
                    "Populate primary_residence_fmv, other_personal_assets_value, etc. for a more defensible assessment."
                )
                notes.append(f"Legacy net_assets fallback: {legacy_net:,.0f}")
            else:
                flags.append(
                    "Legacy net_assets present but source is external without acceptable evidence — excluded"
                )
                mr.append("No supported NPA values available — cannot finalise assessment")
                missing.append(
                    "supported NPA asset values "
                    "(primary_residence_fmv, other_personal_assets_value, etc.)"
                )
                return None, missing, flags, mr, notes
        elif legacy_total is not None and legacy_liab is not None:
            if supported:
                recognised_npa = legacy_total - legacy_liab
                flags.append(
                    "Using legacy total_assets − total_liabilities fallback — "
                    "new explicit NPA fields not populated."
                )
                notes.append(
                    f"Legacy fallback: {legacy_total:,.0f} − {legacy_liab:,.0f} = {recognised_npa:,.0f}"
                )
            else:
                mr.append("No supported NPA values available — cannot finalise assessment")
                missing.append("supported NPA asset values")
                return None, missing, flags, mr, notes
        else:
            missing.append(
                "NPA asset fields: primary_residence_fmv or "
                "other_personal_assets_value / financial_assets_for_npa_value "
                "(or legacy net_assets)"
            )
            return None, missing, flags, mr, notes
    else:
        recognised_npa = (
            other_personal
            + other_re_equity
            + fin_for_npa
            + insurance_sv
            + biz_interest
            + recognised_pr
            - other_liab
        )
        notes.append(
            f"NPA = other_personal({other_personal:,.0f}) "
            f"+ re_equity({other_re_equity:,.0f}) "
            f"+ fin_for_npa({fin_for_npa:,.0f}) "
            f"+ insurance({insurance_sv:,.0f}) "
            f"+ biz({biz_interest:,.0f}) "
            f"+ pr({recognised_pr:,.0f}) "
            f"− liab({other_liab:,.0f}) "
            f"= {recognised_npa:,.0f}"
        )

    return recognised_npa, missing, flags, mr, notes


def _evaluate_financial_assets(
    normalized: dict,
    policy: dict,
    today: date_cls,
) -> tuple[Optional[float], list, list, list, list]:
    """
    Net Financial Assets (NFA) criterion evaluator.
    Pass if recognised_nfa_sgd > SGD 1,000,000.

    Formula:
      recognised_nfa =
          cash_holdings (deposit balance)
          + investment_holdings (investment products)
          + funds_under_management_value (ILP / fund values)
          + cpf_investment_amount (CPFIS only — raw CPF balances are excluded)
          − financial_assets_related_liabilities
            (computed from margin_loan_balance + portfolio_credit_line_balance
             if aggregate field is absent)

    Exclusions (hard-coded):
      - Raw CPF balances (ordinary / special / medisave)
      - DPT / stablecoin values (not present in schema)
      - Non-financial assets

    External manually-keyed values without acceptable evidence are excluded.
    """
    missing: list   = []
    flags:   list   = []
    mr:      list   = []
    notes:   list   = []

    source_is_internal = normalized.get("source_is_internal", False)
    evidence_type      = normalized.get("evidence_type") or ""
    evidence_date      = normalized.get("evidence_date") or ""
    stmt_date          = normalized.get("statement_date") or evidence_date

    # --- Evidence recency ---
    if stmt_date and evidence_type:
        stale, stale_reason = _check_evidence_recency(
            evidence_type or "external_investment_statement", stmt_date, today, policy
        )
        if stale:
            flags.append(stale_reason)
            mr.append(f"Stale financial assets evidence — {stale_reason}")
    elif not source_is_internal and not stmt_date:
        flags.append(
            "statement_date missing for external financial assets — "
            "evidence recency cannot be confirmed"
        )
        mr.append("External financial assets statement date not provided")

    # --- Source control gate ---
    supported, support_reason = _is_value_supported(
        source_is_internal, evidence_type, evidence_date, today, policy
    )

    def _fa_value(field_name: str, label: str) -> float:
        val = normalized.get(field_name) or 0.0
        if val > 0 and not supported:
            flags.append(
                f"{label} ({val:,.0f}) excluded — external manual value without "
                f"acceptable evidence: {support_reason}"
            )
            return 0.0
        return val

    deposit_balance     = _fa_value("cash_holdings",             "cash_holdings")
    investment_products = _fa_value("investment_holdings",       "investment_holdings")
    insurance_inv       = _fa_value("funds_under_management_value", "funds_under_management_value")

    # CPFIS — included if present; document explicitly that raw CPF balances are excluded
    cpfis = normalized.get("cpf_investment_amount") or 0.0
    if cpfis > 0:
        if not supported:
            flags.append(
                f"cpf_investment_amount ({cpfis:,.0f}) excluded — "
                f"external manual value without acceptable evidence: {support_reason}"
            )
            cpfis = 0.0
        else:
            notes.append(
                f"CPFIS included: SGD {cpfis:,.0f} "
                "(assumed CPFIS-eligible investments only — raw CPF balances excluded)"
            )

    component_sum = deposit_balance + investment_products + insurance_inv + cpfis

    # --- Fallback to declared total if no components ---
    declared_total = normalized.get("total_financial_assets")
    if component_sum == 0.0 and declared_total is not None:
        if supported:
            component_sum = declared_total
            flags.append(
                "Using total_financial_assets as aggregate — no component breakdown provided. "
                "Populate cash_holdings, investment_holdings etc. for a more defensible assessment."
            )
        else:
            flags.append(
                f"total_financial_assets ({declared_total:,.0f}) excluded — "
                f"external manual value without component breakdown: {support_reason}"
            )
            missing.append(
                "financial asset components (cash_holdings, investment_holdings) "
                "or acceptable evidence for total_financial_assets"
            )
            mr.append(
                "External total_financial_assets without component breakdown and without "
                "sufficient evidence — cannot support pass"
            )
            return None, missing, flags, mr, notes
    elif component_sum == 0.0 and declared_total is None:
        missing.append(
            "total_financial_assets or financial asset components "
            "(cash_holdings, investment_holdings)"
        )
        return None, missing, flags, mr, notes

    # Cross-check: if declared total and components both present, check consistency
    if declared_total is not None and component_sum != declared_total:
        diff = abs(declared_total - component_sum)
        if diff > 100:
            flags.append(
                f"total_financial_assets ({declared_total:,.0f}) differs from "
                f"component sum ({component_sum:,.0f}) by SGD {diff:,.0f}"
            )

    # --- Related liabilities ---
    margin_loan      = normalized.get("margin_loan_balance") or 0.0
    portfolio_credit = normalized.get("portfolio_credit_line_balance") or 0.0
    declared_liab    = normalized.get("financial_assets_related_liabilities")

    if declared_liab is not None:
        computed_liab = margin_loan + portfolio_credit
        if computed_liab > 0 and abs(declared_liab - computed_liab) > 100:
            flags.append(
                f"financial_assets_related_liabilities ({declared_liab:,.0f}) differs from "
                f"margin_loan_balance + portfolio_credit_line_balance ({computed_liab:,.0f})"
            )
        total_liab = declared_liab
    else:
        total_liab = margin_loan + portfolio_credit
        if total_liab > 0:
            notes.append(
                f"Liabilities computed: margin({margin_loan:,.0f}) "
                f"+ credit({portfolio_credit:,.0f}) = {total_liab:,.0f}"
            )

    # Flag potentially undeducted liabilities on financed positions
    if investment_products > 0 and total_liab == 0 and not source_is_internal:
        flags.append(
            "Investment holdings present but no margin_loan_balance or "
            "portfolio_credit_line_balance declared — if positions are margin-financed, "
            "related liabilities must be deducted"
        )
        mr.append(
            "Financed investment positions may have undeclared margin or credit liabilities"
        )

    recognised_nfa = component_sum - total_liab
    if recognised_nfa < 0:
        flags.append(f"recognised_nfa is negative ({recognised_nfa:,.0f}) after liability deduction")

    notes.append(
        f"NFA = deposits({deposit_balance:,.0f}) "
        f"+ investments({investment_products:,.0f}) "
        f"+ insurance({insurance_inv:,.0f}) "
        f"+ CPFIS({cpfis:,.0f}) "
        f"− liabilities({total_liab:,.0f}) "
        f"= {recognised_nfa:,.0f}"
    )

    return recognised_nfa, missing, flags, mr, notes


# ---------------------------------------------------------------------------
# Layer 2 — Status, confidence, and checker recommendation
# ---------------------------------------------------------------------------

def _compute_status_and_confidence(
    recognised_amount:  Optional[float],
    threshold:          float,
    missing_fields:     list,
    inconsistency_flags: list,
    manual_review_reasons: list,
    policy:             dict,
) -> tuple[bool, str, str, bool, list]:
    """
    Returns: (pass_result, assessment_status, confidence_level, manual_review_required, final_mr_reasons)

    Status logic (precedence order):
    1. recognised_amount is None (critical fields missing or unsupported external value) → pending_info
    2. recognised_amount < threshold → not_eligible
    3. Within 10% above threshold → manual_review, confidence capped at Medium
    4. Any manual_review_reasons (stale evidence, control breach, etc.) → manual_review
    5. Any inconsistency_flags → manual_review, confidence Low
    6. Clean pass with missing supporting fields → eligible, confidence Medium
    7. Fully clean pass → eligible, confidence High
    """
    borderline_pct = policy["borderline_pct"]
    mr_reasons = list(manual_review_reasons)  # work on a copy

    # 1. Critical missing → pending_info
    if recognised_amount is None:
        return False, STATUS_PENDING_INFO, CONFIDENCE_LOW, False, mr_reasons

    # 2. Below threshold → not_eligible
    if recognised_amount < threshold:
        return False, STATUS_NOT_ELIGIBLE, CONFIDENCE_LOW, False, mr_reasons

    # 3. Borderline band
    borderline_upper = threshold * (1.0 + borderline_pct)
    is_borderline = recognised_amount < borderline_upper
    if is_borderline:
        mr_reasons.append(
            f"Result (SGD {recognised_amount:,.0f}) is within "
            f"{int(borderline_pct * 100)}% above threshold (SGD {threshold:,.0f}) — "
            f"borderline upper bound SGD {borderline_upper:,.0f}"
        )

    # 4. Any manual review reason OR 5. inconsistencies → manual_review
    needs_mr = bool(mr_reasons) or bool(inconsistency_flags)
    if needs_mr:
        if inconsistency_flags or (is_borderline and missing_fields):
            confidence = CONFIDENCE_LOW
        else:
            confidence = CONFIDENCE_MEDIUM
        return True, STATUS_MANUAL_REVIEW, confidence, True, mr_reasons

    # 6 & 7. Clean pass
    confidence = CONFIDENCE_MEDIUM if missing_fields else CONFIDENCE_HIGH
    return True, STATUS_ELIGIBLE, confidence, False, mr_reasons


def _generate_checker_recommendation(
    assessment_status:      str,
    confidence_level:       str,
    missing_fields:         list,
    inconsistency_flags:    list,
    manual_review_reasons:  list,
) -> str:
    """
    Deterministic Python-generated checker recommendation string.
    Claude does NOT generate this — it is derived entirely from the decision fields.
    """
    if assessment_status == STATUS_ELIGIBLE:
        if confidence_level == CONFIDENCE_HIGH:
            return (
                "Assessment complete and controls satisfied. "
                "Verify client signature on AI declaration form before reclassification."
            )
        elif confidence_level == CONFIDENCE_MEDIUM:
            return (
                "Assessment passes but some supporting fields are absent. "
                "Request missing documentation before finalising."
            )
        else:
            return (
                "Eligible result but confidence is low. "
                "Review evidence sufficiency independently before approving."
            )

    elif assessment_status == STATUS_MANUAL_REVIEW:
        reasons_str = "; ".join(manual_review_reasons[:2]) if manual_review_reasons else ""
        if reasons_str:
            return f"Manual review required — {reasons_str}."
        if inconsistency_flags:
            return "Manual review required — inconsistencies present. Resolve before approving."
        return "Manual review required before proceeding. Review all flagged items."

    elif assessment_status == STATUS_PENDING_INFO:
        if missing_fields:
            fields_str = ", ".join(missing_fields[:3])
            suffix = " (and others)" if len(missing_fields) > 3 else ""
            return (
                f"Assessment incomplete — obtain {fields_str}{suffix} "
                "before re-running the assessment."
            )
        return "Assessment incomplete — additional information required from RM."

    else:  # not_eligible
        return (
            "Client does not meet the threshold under the selected criterion. "
            "If appropriate, a new assessment under a different criterion "
            "may be initiated by the RM."
        )


def _build_evidence_summary(normalized: dict, criterion: str) -> str:
    """
    Build a human-readable evidence summary string for inclusion in the decision object.
    Does not contain any eligibility conclusion — purely documents what evidence was referenced.
    """
    parts = []
    source = "Internal bank records" if normalized.get("source_is_internal") else "External / RM-provided data"
    parts.append(f"Source: {source}")

    ev_type = normalized.get("evidence_type")
    ev_date = normalized.get("evidence_date")
    if ev_type and ev_date:
        parts.append(f"Evidence: {ev_type} dated {ev_date}")
    elif ev_type:
        parts.append(f"Evidence type: {ev_type} (no date provided)")

    if criterion == "income":
        ps = normalized.get("income_period_start")
        pe = normalized.get("income_period_end")
        if ps and pe:
            parts.append(f"Income period: {ps} to {pe}")
        noa = normalized.get("latest_noa_year")
        if noa:
            parts.append(f"NOA {noa} referenced (supplementary)")

    elif criterion == "net_personal_assets":
        pv_date = normalized.get("property_valuation_date") or normalized.get("valuation_date")
        if pv_date:
            parts.append(f"Property valuation date: {pv_date}")

    elif criterion == "financial_assets":
        stmt = normalized.get("statement_date")
        if stmt:
            parts.append(f"Statement date: {stmt}")
        cpfis = normalized.get("cpf_investment_amount")
        if cpfis:
            parts.append("CPFIS included; raw CPF balances excluded")
        liab = (
            (normalized.get("margin_loan_balance") or 0.0) +
            (normalized.get("portfolio_credit_line_balance") or 0.0)
        )
        if liab > 0:
            parts.append(f"Related liabilities deducted: SGD {liab:,.0f}")

    joint = normalized.get("joint_account_flag")
    if joint:
        parts.append("Joint account flagged (ownership_share applied)")

    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Layer 3 — Memo drafting (Claude-assisted, decision-driven)
# ---------------------------------------------------------------------------

# Criterion labels for display
_CRITERION_LABELS = {
    "income":               "Annual Income ≥ SGD 300,000",
    "net_personal_assets":  "Net Personal Assets > SGD 2,000,000",
    "financial_assets":     "Net Financial Assets > SGD 1,000,000",
}

# Status display
_STATUS_DISPLAY = {
    STATUS_ELIGIBLE:        "✅ Eligible under selected criterion",
    STATUS_NOT_ELIGIBLE:    "❌ Not eligible under selected criterion",
    STATUS_PENDING_INFO:    "⏳ Pending information — assessment incomplete",
    STATUS_MANUAL_REVIEW:   "⚠️ Manual review required",
}

GENERATE_SYSTEM_PROMPT = """\
You are a compliance specialist drafting a formal Accredited Investor (AI) assessment memo
for internal RM use at a private bank in Singapore.

This is an internal compliance document — not a client-facing communication.

Rules (non-negotiable):
- Follow the section structure provided exactly. Do not add, remove, or reorder sections.
- Use the exact figures from the structured input. Do not round eligibility amounts.
- Explicitly name every inconsistency and missing field — do not soften or omit any.
- The RM Declaration and Risk Disclosure sections must appear verbatim as given.
- Do not use vague language: "it appears", "it seems", "broadly", "generally".
- Never say "AI-approved", "final approval", "customer qualifies overall", or "approved as Accredited Investor".
- Use instead: "eligible under selected criterion", "not eligible under selected criterion",
  "pending information", "manual review required", "draft memo for checker review".
- The checker confirms or rejects — this is a draft only.
- Tone: formal, precise, audit-ready. Not conversational.
- Target length: under 3000 characters for Telegram delivery.

Telegram markdown:
- *bold* for section headers only
- ✅ ❌ ⚠️ ⏳ for status lines
- − for bullet points
- No markdown headers (#), no tables, no nested bullets\
"""


def _build_memo_prompt(result: AIDecisionResult) -> str:
    """Build the user-prompt sent to Claude for memo drafting."""
    criterion_label = _CRITERION_LABELS.get(result.selected_criterion, result.selected_criterion)
    status_display  = _STATUS_DISPLAY.get(result.assessment_status, result.assessment_status)
    amount_str      = (
        f"SGD {result.recognised_amount_sgd:,.0f}"
        if result.recognised_amount_sgd is not None
        else "Not determinable"
    )
    missing_str       = "; ".join(result.missing_fields)         if result.missing_fields         else "None"
    flags_str         = "; ".join(result.inconsistency_flags)    if result.inconsistency_flags    else "None"
    mr_reasons_str    = "; ".join(result.manual_review_reasons)  if result.manual_review_reasons  else "None"

    return f"""\
Draft a formal Accredited Investor assessment memo for {result.customer_name}.

Structured decision inputs (do not modify these values):
- Customer: {result.customer_name} ({result.customer_id or 'ID not provided'})
- Selected criterion: {criterion_label}
- Threshold: SGD {result.threshold_sgd:,.0f}
- Recognised amount: {amount_str}
- Pass result: {result.pass_result}
- Assessment status: {result.assessment_status}
- Confidence: {result.confidence_level}
- Manual review required: {result.manual_review_required}
- Manual review reasons: {mr_reasons_str}
- Missing fields: {missing_str}
- Inconsistency flags: {flags_str}
- Evidence summary: {result.evidence_summary}
- Checker recommendation: {result.checker_recommendation}
- Joint account flag: {result.joint_account_flag}
- Checker status: {result.checker_status}

Generate the memo using this exact section structure. Do not change section order or headings.

*Accredited Investor Assessment — {result.customer_name}*
_Draft memo for checker review_

*Eligibility Basis*
[State the selected criterion and threshold. One sentence only.]

*Recognised Amount*
[State the recognised amount and whether it meets the threshold. Cite the exact figure.]

*Evidence and Source*
[Summarise the evidence referenced. Note source classification (internal/external).]

*Validation Notes*
[List validation checks performed. Name any inconsistency flags explicitly, or confirm clean.]

*Missing Information*
[List each missing field, or state: No missing required fields.]

*Assessment Outcome*
{status_display}
Confidence: {result.confidence_level.upper()}
[1–2 sentences of plain reasoning. No invented logic or values.]

*Manual Review*
[If manual_review_required is True: list the manual review reasons.
 If False: state "No manual review required."]

*Checker Recommendation*
{result.checker_recommendation}

*RM Declaration*
This memo was generated by Aureus RM Copilot based on data provided by the relationship manager. The RM is responsible for verifying the accuracy of all input data and for obtaining the client's signed Accredited Investor declaration form prior to any reclassification.

*Risk Disclosure*
Accredited Investors are subject to reduced regulatory safeguards under the Securities and Futures Act (Cap. 289). This document does not constitute a determination of eligibility. Final sign-off requires review and approval by an authorised checker.

_Draft for internal RM use only. Not for client distribution. Checker status: {result.checker_status}._\
"""


def _format_summary_card(result: AIDecisionResult) -> str:
    """
    Generate a structured summary card for the Telegram response.
    Displayed before the Claude-drafted memo.
    All content is deterministic — no Claude involvement.
    """
    criterion_label = _CRITERION_LABELS.get(result.selected_criterion, result.selected_criterion)
    status_display  = _STATUS_DISPLAY.get(result.assessment_status, result.assessment_status)
    amount_str      = (
        f"SGD {result.recognised_amount_sgd:,.0f}"
        if result.recognised_amount_sgd is not None
        else "Not determinable"
    )
    missing_str = (
        "\n".join(f"  − {f}" for f in result.missing_fields)
        if result.missing_fields
        else "  None"
    )
    flags_str = (
        "\n".join(f"  ⚠️ {f}" for f in result.inconsistency_flags[:5])
        if result.inconsistency_flags
        else "  None"
    )

    card_lines = [
        f"*AI Assessment — {result.customer_name}*",
        "",
        f"*Criterion:* {criterion_label}",
        f"*Recognised Amount:* {amount_str}",
        f"*Threshold:* SGD {result.threshold_sgd:,.0f}",
        f"*Outcome:* {status_display}",
        f"*Confidence:* {result.confidence_level}",
        "",
        f"*Missing Items:*\n{missing_str}",
        "",
        f"*Flags:*\n{flags_str}",
        "",
        f"*Checker Recommendation:*\n  {result.checker_recommendation}",
        "",
        f"_Checker status: {result.checker_status} | For internal RM use only._",
    ]
    return "\n".join(card_lines)


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class AIApprovalAgent:
    """
    Internal specialist agent for Singapore Accredited Investor eligibility assessment.

    Implements the generate(command, ctx) interface expected by AureusOrchestrator.
    Not user-facing — all output is routed through AureusOrchestrator → Aureus.

    Layer responsibilities:
    - assess()            — deterministic engine, no Claude, returns AIDecisionResult
    - format_summary_card() — pure Python summary card string
    - generate()          — calls assess() + Claude memo, returns summary + memo combined
    """

    def __init__(self, claude_service, sheets_service=None):
        self.claude = claude_service
        self.sheets = sheets_service
        logger.info("AIApprovalAgent: initialised (deterministic 3-layer engine)")

    # ------------------------------------------------------------------
    # Public interface — matches specialist agent contract
    # ------------------------------------------------------------------

    async def generate(self, command: str, ctx: dict) -> str:
        """
        Generate the full AI assessment output (summary card + draft memo).
        Called by AureusOrchestrator.

        Returns a single string: summary_card + visual separator + Claude memo.
        The summary card is deterministic; the memo is Claude-drafted from structured fields.
        """
        logger.info("AIApprovalAgent.generate | command=%s", command)

        ai_data       = ctx.get("ai_assessment_data") or {}
        customer      = ctx.get("profile") or ctx.get("customer", {})
        customer_name = (
            ctx.get("customer_name")
            or customer.get("preferred_name")
            or customer.get("full_name")
            or "Unknown Client"
        )
        customer_id = customer.get("customer_id", "")
        criterion   = ctx.get("criterion")  # pre-normalised by CommandRouter
        is_mock     = ctx.get("is_mock", False)

        if not ai_data:
            return (
                f"❌ No AI assessment data found for *{customer_name}*.\n\n"
                "Ensure the `AI_Assessment` tab has a record for this client, "
                "or run:\n`python scripts/bootstrap_v7_ai_fields.py`"
            )

        if not criterion:
            return (
                f"❌ No criterion selected for *{customer_name}*.\n\n"
                "Please specify: `income`, `net_personal_assets`, or `financial_assets`."
            )

        result       = self.assess(ai_data, criterion=criterion,
                                   customer_name=customer_name, customer_id=customer_id)
        summary_card = _format_summary_card(result)
        memo_prompt  = _build_memo_prompt(result)

        # --- Claude memo drafting ---
        _SEPARATOR = "\n\n" + "─" * 22 + "\n\n"
        try:
            memo = await self.claude.generate_raw(
                system_prompt=GENERATE_SYSTEM_PROMPT,
                user_prompt=memo_prompt,
                is_mock=is_mock,
            )
        except Exception as exc:
            logger.warning("Claude unavailable for AI assessment memo: %s", exc)
            memo = _fallback_memo(result)

        return summary_card + _SEPARATOR + memo

    # ------------------------------------------------------------------
    # Deterministic assessment core (no Claude — fully testable)
    # ------------------------------------------------------------------

    def assess(
        self,
        data:           dict,
        criterion:      str,
        customer_name:  str = "the client",
        customer_id:    str = "",
    ) -> AIDecisionResult:
        """
        Evaluate AI eligibility for the RM-selected criterion only.

        criterion: "income" | "net_personal_assets" | "financial_assets"
        Any other value (including None) returns pending_info with an explanation.

        Pure Python — no Claude, no I/O, fully testable.
        """
        today = date_cls.today()

        # Layer 1: normalise input
        normalized = normalize_assessment_input(data)

        # Joint account metadata (shared across all criteria)
        joint_flag = normalized.get("joint_account_flag", False)
        joint_note = str(normalized.get("joint_account_note") or "")

        # --- Dispatch to criterion evaluator ---
        _EVALUATORS = {
            "income":               _evaluate_income,
            "net_personal_assets":  _evaluate_net_personal_assets,
            "financial_assets":     _evaluate_financial_assets,
        }
        _THRESHOLDS = {
            "income":               INCOME_THRESHOLD,
            "net_personal_assets":  NET_PERSONAL_ASSETS_THRESHOLD,
            "financial_assets":     FINANCIAL_ASSETS_THRESHOLD,
        }

        evaluator = _EVALUATORS.get(criterion)
        if evaluator is None:
            return AIDecisionResult(
                customer_id=customer_id,
                customer_name=customer_name,
                selected_criterion=str(criterion or ""),
                recognised_amount_sgd=None,
                threshold_sgd=0.0,
                pass_result=False,
                assessment_status=STATUS_PENDING_INFO,
                confidence_level=CONFIDENCE_LOW,
                missing_fields=[
                    f"selected_criterion '{criterion}' is not recognised — "
                    "must be income, net_personal_assets, or financial_assets"
                ],
                inconsistency_flags=[],
                manual_review_required=False,
                manual_review_reasons=[],
                joint_account_flag=joint_flag,
                joint_account_note=joint_note,
                checker_status="pending_review",
                checker_recommendation=(
                    f"Invalid criterion '{criterion}'. "
                    "Please select: income, net_personal_assets, or financial_assets."
                ),
                evidence_summary="",
                computation_notes=[],
            )

        threshold = _THRESHOLDS[criterion]
        recognised, missing, flags, mr_reasons, notes = evaluator(
            normalized, AI_ASSESSMENT_POLICY, today
        )

        pass_result, status, confidence, mr_required, mr_reasons_final = (
            _compute_status_and_confidence(
                recognised, threshold, missing, flags, mr_reasons, AI_ASSESSMENT_POLICY
            )
        )

        checker_rec     = _generate_checker_recommendation(
            status, confidence, missing, flags, mr_reasons_final
        )
        evidence_summary = _build_evidence_summary(normalized, criterion)

        return AIDecisionResult(
            customer_id=customer_id,
            customer_name=customer_name,
            selected_criterion=criterion,
            recognised_amount_sgd=recognised,
            threshold_sgd=threshold,
            pass_result=pass_result,
            assessment_status=status,
            confidence_level=confidence,
            missing_fields=missing,
            inconsistency_flags=flags,
            manual_review_required=mr_required,
            manual_review_reasons=mr_reasons_final,
            joint_account_flag=joint_flag,
            joint_account_note=joint_note,
            checker_status="pending_review",
            checker_recommendation=checker_rec,
            evidence_summary=evidence_summary,
            computation_notes=notes,
        )

    def format_summary_card(self, result: AIDecisionResult) -> str:
        """Public wrapper for summary card formatting. Useful for tests and command router."""
        return _format_summary_card(result)


# ---------------------------------------------------------------------------
# Fallback memo (Claude unavailable)
# ---------------------------------------------------------------------------

def _fallback_memo(result: AIDecisionResult) -> str:
    """
    Template-based memo when Claude is unavailable.
    Produces a structurally complete but plain-text memo from the decision object.
    No invented content — all values come directly from AIDecisionResult fields.
    """
    criterion_label = _CRITERION_LABELS.get(result.selected_criterion, result.selected_criterion)
    status_display  = _STATUS_DISPLAY.get(result.assessment_status, result.assessment_status)
    amount_str      = (
        f"SGD {result.recognised_amount_sgd:,.0f}"
        if result.recognised_amount_sgd is not None
        else "Not determinable"
    )

    lines = [
        f"*Accredited Investor Assessment — {result.customer_name}*",
        "_Draft memo for checker review (template — Claude unavailable)_",
        "",
        "*Eligibility Basis*",
        f"- {criterion_label}",
        "",
        "*Recognised Amount*",
        f"- Recognised: {amount_str}",
        f"- Threshold: SGD {result.threshold_sgd:,.0f}",
        "",
        "*Evidence and Source*",
        f"- {result.evidence_summary or 'Not provided'}",
        "",
        "*Validation Notes*",
    ]

    if result.inconsistency_flags:
        for flag in result.inconsistency_flags:
            lines.append(f"- ⚠️ {flag}")
    else:
        lines.append("- No inconsistencies detected")

    lines += [
        "",
        "*Missing Information*",
    ]
    if result.missing_fields:
        for f in result.missing_fields:
            lines.append(f"- {f}")
    else:
        lines.append("- No missing required fields")

    lines += [
        "",
        f"*Assessment Outcome*",
        f"{status_display}",
        f"Confidence: {result.confidence_level.upper()}",
        "",
        "*Manual Review*",
    ]
    if result.manual_review_reasons:
        for r in result.manual_review_reasons:
            lines.append(f"- {r}")
    else:
        lines.append("- No manual review required")

    lines += [
        "",
        "*Checker Recommendation*",
        f"- {result.checker_recommendation}",
        "",
        "*RM Declaration*",
        (
            "This memo was generated by Aureus RM Copilot based on data provided by the "
            "relationship manager. The RM is responsible for verifying input data accuracy "
            "and obtaining the client's signed AI declaration form prior to reclassification."
        ),
        "",
        "*Risk Disclosure*",
        (
            "Accredited Investors are subject to reduced regulatory safeguards under the "
            "Securities and Futures Act (Cap. 289). This document does not constitute a "
            "determination of eligibility. Final sign-off requires checker approval."
        ),
        "",
        f"_Draft for internal RM use only. Checker status: {result.checker_status}._",
    ]

    return "\n".join(lines)
