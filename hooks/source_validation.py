"""
source_validation.py
─────────────────────────────────────────────────────────────────────────────
Aureus RM Copilot — Source Validation Hook
Invoked after tool calls return results, before the response is finalised.

Responsibility:
    Validate that material factual claims in the generated content map to
    data actually returned by MCP tool calls.  Unsupported claims are
    collected and surfaced to the response layer so the RM user is never
    silently exposed to hallucinated figures.

Integration point:
    Call this hook in the command dispatcher after all tool results are
    collected and the draft response text is available.  Inspect
    `validated` and `unsupported_claims` before finalising the response.

Extension points (marked inline with # EXTENSION POINT):
    - Replace heuristic string-search with embedding-based similarity
      against a vector knowledge base.
    - Plug in a structured fact-extraction pipeline for richer claim parsing.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE REQUIREMENTS
#
# Maps claim type labels to the MCP tool(s) whose output is considered an
# authoritative source for that claim type.  If a claim of that type is
# detected in the response but none of the listed tools returned data, the
# claim is flagged as unsupported.
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_REQUIREMENTS: dict[str, list[str]] = {
    "financial_figure":      ["get_stock_data", "get_financials", "get_portfolio"],
    "price_target":          ["get_analyst_ratings", "get_consensus_estimates"],
    "analyst_name":          ["get_analyst_ratings", "get_research_reports"],
    "date_specific_claim":   ["get_news", "get_events", "get_filings"],
    "macro_statistic":       ["get_macro_data", "get_economic_indicators"],
    "fund_performance":      ["get_fund_data", "get_portfolio"],
    "regulatory_reference":  ["get_compliance_data", "get_regulatory_filings"],
}

# ─────────────────────────────────────────────────────────────────────────────
# CLAIM DETECTION PATTERNS
#
# Each entry describes a class of claim that requires source backing.
# These are intentionally conservative — false positives get a "note" severity
# so the RM can review without being blocked.
# ─────────────────────────────────────────────────────────────────────────────

CLAIM_PATTERNS: list[dict] = [
    # Specific dollar / currency figures (e.g. "$4.2B", "SGD 1.3M", "USD 82.5")
    {
        "label": "financial_figure",
        "pattern": re.compile(
            r"(?:USD|SGD|HKD|EUR|GBP|\$)\s*[\d,]+(?:\.\d+)?(?:\s*[BMK](?:illion|n)?)?\b",
            re.IGNORECASE,
        ),
        "severity": "warning",
        "reason": "Specific financial figure detected with no matching value in tool results.",
    },
    # Analyst price targets ("price target of $120", "$95 target")
    {
        "label": "price_target",
        "pattern": re.compile(
            r"(?:price\s+target|PT)\s+(?:of\s+)?\$[\d,]+(?:\.\d+)?"
            r"|\$[\d,]+(?:\.\d+)?\s+(?:price\s+)?target",
            re.IGNORECASE,
        ),
        "severity": "warning",
        "reason": "Analyst price target cited with no matching analyst data in tool results.",
    },
    # Named analyst attribution ("according to Morgan Stanley", "Goldman Sachs estimates")
    {
        "label": "analyst_name",
        "pattern": re.compile(
            r"\b(Morgan Stanley|Goldman Sachs|JPMorgan|UBS|Citi(?:group)?|"
            r"Barclays|Deutsche Bank|HSBC|Macquarie|DBS|OCBC|CGS.?CIMB|"
            r"Jefferies|Bernstein|BofA|Bank of America)\b",
            re.IGNORECASE,
        ),
        "severity": "note",
        "reason": "Named analyst/bank referenced — verify that data from this source appears in tool results.",
    },
    # Date-specific claims ("on 15 March", "as of Q3 2024", "in FY2023")
    {
        "label": "date_specific_claim",
        "pattern": re.compile(
            r"\b(?:as\s+of|on|in|during)\s+"
            r"(?:Q[1-4]\s+\d{4}|\d{1,2}\s+\w+\s+\d{4}|FY\d{4}|H[12]\s+\d{4})\b",
            re.IGNORECASE,
        ),
        "severity": "note",
        "reason": "Date-specific claim detected — confirm the relevant period is covered by tool results.",
    },
    # Percentage metrics without an obvious conversational modifier
    {
        "label": "financial_figure",
        "pattern": re.compile(
            r"\b\d{1,3}(?:\.\d+)?%\s+(?:growth|decline|return|yield|margin|increase|decrease)\b",
            re.IGNORECASE,
        ),
        "severity": "warning",
        "reason": "Specific percentage metric cited — verify it appears in retrieved data.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _flatten_tool_text(tool_results: dict) -> str:
    """
    Concatenate all tool result values into a single searchable string.
    Handles nested dicts, lists, and scalar values defensively.
    """
    parts: list[str] = []

    def _extract(obj) -> None:
        if obj is None:
            return
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _extract(v)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _extract(item)
        else:
            parts.append(str(obj))

    _extract(tool_results)
    return " ".join(parts)


def _tools_called(tool_results: dict) -> list[str]:
    """Return the list of tool names that were actually invoked."""
    return list(tool_results.keys()) if tool_results else []


def _source_present(label: str, tools_called: list[str]) -> bool:
    """
    Check whether at least one authoritative source tool for this claim type
    was called and returned data.
    """
    required = SOURCE_REQUIREMENTS.get(label, [])
    return any(t in tools_called for t in required)


def _value_in_tool_output(matched_text: str, tool_text: str) -> bool:
    """
    Heuristic: check whether the numeric core of a matched claim appears
    anywhere in the flattened tool output.

    EXTENSION POINT: Replace this with an embedding-similarity lookup against
    a vector knowledge base for richer semantic matching:

        from myorg.vector_kb import semantic_search
        hits = semantic_search(matched_text, namespace="tool_results", top_k=3)
        return any(hit.score > SIMILARITY_THRESHOLD for hit in hits)
    """
    # Extract digits+decimals from the matched claim for a loose numeric match
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", matched_text)
    if not numbers:
        return True  # no specific number to verify — can't assert unsupported
    return any(n in tool_text for n in numbers)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN HOOK FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def run_source_validation(
    response_text: str,
    tool_results: Optional[dict],
    command_context: str,
) -> dict:
    """
    Post-tool-call source validation hook.

    Parameters
    ----------
    response_text : str
        Draft response text to validate.
    tool_results : dict | None
        Mapping of { tool_name: tool_output } for all tools called during
        this request.  Pass None or an empty dict if no tools were called.
    command_context : str
        Originating command slug (e.g. "stock-brief", "next-best-action").

    Returns
    -------
    dict with keys:
        validated           (bool)          True iff no unsupported claims found.
        unsupported_claims  (list[dict])    Claims that could not be sourced.
        source_map          (dict)          {claim_label: [tools_found]} summary.
        warning_text        (str | None)    Human-readable summary for the RM,
                                            or None if everything validated.

    Each unsupported_claim dict:
        claim_text  (str)   Matched text excerpt.
        reason      (str)   Explanation of why it is flagged.
        severity    (str)   "note" or "warning".
        label       (str)   Claim type label.
    """
    # ── Defensive normalisation ───────────────────────────────────────────────
    if not tool_results:
        tool_results = {}
        logger.debug(
            "source_validation: no tool results provided for command=%s",
            command_context,
        )

    tool_text = _flatten_tool_text(tool_results)
    called_tools = _tools_called(tool_results)

    unsupported_claims: list[dict] = []
    source_map: dict[str, list[str]] = {}

    # ── Scan response for claim patterns ────────────────────────────────────
    for rule in CLAIM_PATTERNS:
        matches = rule["pattern"].findall(response_text)
        if not matches:
            continue

        # Build the source_map entry for this label
        required_tools = SOURCE_REQUIREMENTS.get(rule["label"], [])
        found_tools = [t for t in required_tools if t in called_tools]
        source_map[rule["label"]] = found_tools

        for match in rule["pattern"].finditer(response_text):
            matched_text = match.group(0)

            # Determine if this specific value appears anywhere in tool output
            value_found = _value_in_tool_output(matched_text, tool_text)
            source_tool_present = _source_present(rule["label"], called_tools)

            if not value_found and not source_tool_present:
                claim = {
                    "claim_text": matched_text,
                    "reason": rule["reason"],
                    "severity": rule["severity"],
                    "label": rule["label"],
                }
                unsupported_claims.append(claim)
                logger.warning(
                    "Unsupported claim | label=%s severity=%s command=%s text=%r",
                    rule["label"],
                    rule["severity"],
                    command_context,
                    matched_text,
                )

    # Deduplicate claims with identical text + label
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for c in unsupported_claims:
        key = (c["claim_text"], c["label"])
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    unsupported_claims = deduped

    validated = len(unsupported_claims) == 0

    # ── Build human-readable warning text ───────────────────────────────────
    warning_text: Optional[str] = None
    if unsupported_claims:
        warning_lines = [
            f"Source validation flagged {len(unsupported_claims)} unsupported claim(s) "
            f"in the '{command_context}' response:\n"
        ]
        for i, c in enumerate(unsupported_claims, 1):
            warning_lines.append(
                f"  {i}. [{c['severity'].upper()}] \"{c['claim_text']}\" — {c['reason']}"
            )
        warning_text = "\n".join(warning_lines)

    result = {
        "validated": validated,
        "unsupported_claims": unsupported_claims,
        "source_map": source_map,
        "warning_text": warning_text,
    }

    logger.info(
        "Source validation complete | validated=%s unsupported=%d command=%s",
        validated,
        len(unsupported_claims),
        command_context,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# EXTENSION POINT — Vector knowledge base integration
# ─────────────────────────────────────────────────────────────────────────────
#
# Replace the heuristic _value_in_tool_output() function with a semantic
# search against an internal vector knowledge base to validate claims against
# a richer corpus (e.g. ingested research PDFs, CRM notes, filing text):
#
#   from myorg.vector_kb import VectorKnowledgeBase
#   _kb = VectorKnowledgeBase(namespace="aureus-rm")
#
#   def _value_in_tool_output(matched_text: str, tool_text: str) -> bool:
#       hits = _kb.search(matched_text, top_k=5)
#       return any(hit.score > 0.82 for hit in hits)
#
# Also consider adding a `confidence_score` field to each unsupported_claim
# dict to allow downstream consumers to apply their own thresholds.
# ─────────────────────────────────────────────────────────────────────────────
