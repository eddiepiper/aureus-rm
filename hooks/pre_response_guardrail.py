"""
pre_response_guardrail.py
─────────────────────────────────────────────────────────────────────────────
Aureus RM Copilot — Pre-Response Guardrail Hook
Invoked before Claude generates a final response.

Responsibility:
    Scan draft response text for prohibited language patterns that would
    violate compliance standards for a regulated wealth-management context
    (MAS/SFC/FCA suitability obligations, fair-dealing obligations, etc.).

Integration point:
    Call this hook from the command dispatcher BEFORE the final response is
    returned to the RM user.  If `passed` is False, surface `modified_text`
    (never the raw draft) to the user.

Extension points:
    - Replace PROHIBITED_PATTERNS with a dynamic rules-engine fetch
      (e.g. pull from a compliance rule database at startup).
    - Wire `flags` into a compliance audit trail / SIEM event stream.
    - Add a `dry_run` parameter to log-only mode without text modification.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PROHIBITED PATTERNS
#
# Each rule dict:
#   pattern               – compiled regex
#   label                 – machine-readable rule identifier
#   severity              – "block"   → replace phrase + append disclaimer
#                           "warning" → append note, no substitution
#   compliant_replacement – substitution string for "block" rules; None for warnings
# ─────────────────────────────────────────────────────────────────────────────

PROHIBITED_PATTERNS: list[dict] = [
    # ── Guaranteed-return language ──────────────────────────────────────────
    {
        "pattern": re.compile(
            r"\bguaranteed\s+(return|income|profit)\b", re.IGNORECASE
        ),
        "label": "guaranteed_return",
        "severity": "block",
        "compliant_replacement": "potential return (subject to market risk)",
    },
    # ── Risk-free language ───────────────────────────────────────────────────
    {
        "pattern": re.compile(
            r"\b(risk[- ]free|no[- ]risk|zero[- ]risk)\b", re.IGNORECASE
        ),
        "label": "risk_free_language",
        "severity": "block",
        "compliant_replacement": "lower-risk",
    },
    # ── Certainty / no-lose language ─────────────────────────────────────────
    {
        "pattern": re.compile(
            r"\b(will\s+definitely|certain\s+to|sure\s+to|can'?t\s+lose|no[- ]brainer)\b",
            re.IGNORECASE,
        ),
        "label": "certainty_language",
        "severity": "block",
        "compliant_replacement": "may",
    },
    # ── Direct buy recommendations ───────────────────────────────────────────
    {
        "pattern": re.compile(
            r"\b(I\s+recommend\s+you\s+buy|you\s+should\s+buy|you\s+must\s+invest)\b",
            re.IGNORECASE,
        ),
        "label": "direct_buy_recommendation",
        "severity": "block",
        "compliant_replacement": (
            "this may be worth discussing with your client as a potential option"
        ),
    },
    # ── Absolute certainty ───────────────────────────────────────────────────
    {
        "pattern": re.compile(
            r"\b(100%\s+sure|absolutely\s+certain)\b", re.IGNORECASE
        ),
        "label": "absolute_certainty",
        "severity": "block",
        "compliant_replacement": "highly probable",
    },
    # ── Standalone price targets without source attribution ──────────────────
    # Matches "$120 target" / "$1,200 price target" that are NOT immediately
    # followed by an attribution keyword (from/by/per/via/set by).
    # Severity is WARNING — the RM may have proper attribution elsewhere; flag
    # it for manual review rather than silently editing the figure.
    {
        "pattern": re.compile(
            r"\$[\d,]+(?:\.\d+)?\s+(?:price\s+)?target"
            r"(?!\s+(?:from|by|according|per|via|set\s+by))",
            re.IGNORECASE,
        ),
        "label": "unattributed_price_target",
        "severity": "warning",
        "compliant_replacement": None,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DISCLAIMER / FOOTER STRINGS
# ─────────────────────────────────────────────────────────────────────────────

BLOCK_DISCLAIMER = (
    "\n\n---\n"
    "**Compliance Notice:** This content has been automatically reviewed and "
    "certain language has been adjusted to meet regulatory fair-dealing "
    "standards. Ensure all investment recommendations align with the client's "
    "suitability profile and applicable regulations before sharing externally."
)

WARNING_NOTE_TEMPLATE = (
    "\n\n> **Compliance Note ({label}):** The above response contains "
    "language that may require review before sharing with clients. "
    "Please verify accuracy and attribution."
)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN HOOK FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def run_guardrail(
    response_text: str,
    command_context: str,
    client_context: Optional[dict] = None,
) -> dict:
    """
    Pre-response compliance guardrail.

    Parameters
    ----------
    response_text : str
        Raw draft response from Claude before delivery to the RM user.
    command_context : str
        Originating command slug (e.g. "stock-brief", "meeting-pack").
        Used to contextualise flags; reserved for context-sensitive rule
        routing in future versions.
    client_context : dict, optional
        Validated client context record (see schemas/client_context.json).
        Reserved for future use — stricter rules for Mass Affluent vs
        Institutional segments can be applied here.

    Returns
    -------
    dict with keys:
        passed           (bool)       True iff no block-severity rules triggered.
        flags            (list[dict]) All violations found (both severities).
        modified_text    (str)        Compliant version of the response.
        warning_appended (bool)       Whether any footer text was added.

    Each flag dict:
        pattern      (str)            Regex pattern string that matched.
        matched_text (str)            Exact substring that triggered the rule.
        location     (int)            Character offset in the original text.
        severity     (str)            "block" or "warning".
        label        (str)            Rule identifier.
        replacement  (str | None)     Substitution used (None for warnings).
    """
    flags: list[dict] = []
    modified_text: str = response_text
    has_blocks = False
    has_warnings = False

    # ── Scan original text for all violations ────────────────────────────────
    for rule in PROHIBITED_PATTERNS:
        for match in rule["pattern"].finditer(response_text):
            flag = {
                "pattern": rule["pattern"].pattern,
                "matched_text": match.group(0),
                "location": match.start(),
                "severity": rule["severity"],
                "label": rule["label"],
                "replacement": rule.get("compliant_replacement"),
            }
            flags.append(flag)
            logger.warning(
                "Guardrail flag | label=%s severity=%s command=%s matched=%r",
                rule["label"],
                rule["severity"],
                command_context,
                match.group(0),
            )
            if rule["severity"] == "block":
                has_blocks = True
            else:
                has_warnings = True

    # ── Apply block-level substitutions ──────────────────────────────────────
    # Run each pattern substitution on the evolving modified_text so that
    # successive replacements build on each other correctly.
    if has_blocks:
        for rule in PROHIBITED_PATTERNS:
            if rule["severity"] == "block" and rule.get("compliant_replacement"):
                modified_text = rule["pattern"].sub(
                    rule["compliant_replacement"], modified_text
                )

    # ── Append compliance footers ─────────────────────────────────────────────
    warning_appended = False

    if has_blocks:
        modified_text += BLOCK_DISCLAIMER
        warning_appended = True

    if has_warnings:
        warning_labels = list({f["label"] for f in flags if f["severity"] == "warning"})
        for label in warning_labels:
            modified_text += WARNING_NOTE_TEMPLATE.format(label=label)
        warning_appended = True

    passed = not has_blocks

    result = {
        "passed": passed,
        "flags": flags,
        "modified_text": modified_text,
        "warning_appended": warning_appended,
    }

    if flags:
        logger.info(
            "Guardrail complete | passed=%s total_flags=%d blocks=%s warnings=%s command=%s",
            passed,
            len(flags),
            has_blocks,
            has_warnings,
            command_context,
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# EXTENSION POINT — Future rules-engine integration
# ─────────────────────────────────────────────────────────────────────────────
#
# To integrate with an external compliance rules engine, replace or supplement
# PROHIBITED_PATTERNS at application startup:
#
#   from myorg.compliance import fetch_active_rules
#   PROHIBITED_PATTERNS = fetch_active_rules(jurisdiction="SGP", segment="HNW")
#
# Each fetched rule must conform to the same dict shape as the entries above:
#   { "pattern": <compiled regex>, "label": str, "severity": str,
#     "compliant_replacement": str | None }
#
# For audit trail integration, forward the `flags` list from the return value
# to your SIEM or compliance event bus after every call.
# ─────────────────────────────────────────────────────────────────────────────
