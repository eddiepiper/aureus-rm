"""
crm_logger.py
─────────────────────────────────────────────────────────────────────────────
Aureus RM Copilot — CRM Logger Hook
Invoked after response generation for meeting-pack and next-best-action
commands to produce a structured audit/activity log.

Responsibility:
    Build a well-formed JSON log record from each significant command
    execution and dispatch it to one or more configured destinations:
    local JSONL file (dev/test), CRM write-back stub, or REST API stub.

Integration point:
    Call dispatch_log() at the end of any command handler that should leave
    an activity trail in the CRM or internal notes system.

Extension points (marked inline):
    - Implement log_to_crm() when a CRM SDK / API client is available.
    - Implement log_to_api() when an internal event bus endpoint is confirmed.
    - Extend LogRecord with additional fields (e.g. language_model_version,
      latency_ms) without breaking existing consumers.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
#
# In production, load this from environment variables or a config service
# rather than hardcoding values here.
# ─────────────────────────────────────────────────────────────────────────────

CONFIG: dict = {
    # Master switch — set False to disable all logging from this module.
    "enabled": True,

    # Write records to a local JSONL file (always on in dev/test).
    "log_to_file": True,

    # Write records to the CRM system (stub — NotImplementedError until wired up).
    "log_to_crm": False,

    # POST records to an internal REST API (stub — NotImplementedError until wired up).
    "log_to_api": False,

    # Path for the local JSONL log file.
    # Override via LOG_FILE_PATH environment variable in production.
    "log_file_path": os.environ.get(
        "AUREUS_LOG_FILE_PATH",
        os.path.join(os.path.dirname(__file__), "..", "logs", "crm_activity.jsonl"),
    ),

    # Commands that should be logged (empty list = log all commands).
    "log_commands": ["meeting-pack", "next-best-action"],

    # Whether to include the full response text in the log record.
    # Set False in production if PII / confidentiality is a concern.
    "include_full_text": True,
}


# ─────────────────────────────────────────────────────────────────────────────
# LOG RECORD BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_record(
    command: str,
    client_id: Optional[str],
    response_text: str,
    metadata: dict,
) -> dict:
    """
    Construct a structured log record from the command execution context.

    Returns a dict that is safe to serialise to JSON.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Deterministic hash of the output content for deduplication / tamper detection
    output_hash = hashlib.sha256(response_text.encode("utf-8")).hexdigest()

    # Short content summary — first 300 characters of the response, stripped of
    # Markdown formatting characters to keep the summary readable in CRM notes.
    _clean = response_text.replace("#", "").replace("*", "").replace("`", "")
    content_summary = " ".join(_clean.split())[:300]

    # Tags: combine command-derived tags with any provided in metadata
    base_tags = [command]
    if client_id:
        base_tags.append(f"client:{client_id}")
    extra_tags = metadata.get("tags", [])
    tags = list(dict.fromkeys(base_tags + extra_tags))  # deduplicate, preserve order

    record: dict = {
        "timestamp": timestamp,
        "command": command,
        "client_id": client_id,
        "rm_user": metadata.get("rm_user"),
        "output_hash": output_hash,
        "content_summary": content_summary,
        "tags": tags,
        # Optional extended metadata from the caller
        "model_version": metadata.get("model_version"),
        "session_id": metadata.get("session_id"),
        "latency_ms": metadata.get("latency_ms"),
        "data_sources": metadata.get("data_sources", []),
    }

    if CONFIG.get("include_full_text"):
        record["full_text"] = response_text

    return record


# ─────────────────────────────────────────────────────────────────────────────
# LOG DISPATCHER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class LogDispatcher:
    """
    Routes log records to configured destinations.

    Methods are intentionally kept as instance methods so the class can be
    subclassed or instantiated with a custom config for testing.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or CONFIG

    # ── Local file sink (JSONL) ───────────────────────────────────────────────

    def log_to_file(self, record: dict, path: Optional[str] = None) -> None:
        """
        Append a log record to a local JSONL (JSON Lines) file.

        Each line is a fully self-contained JSON object so the file can be
        streamed, tailed, or processed with standard tooling (jq, pandas, etc.).

        Parameters
        ----------
        record : dict
            Structured log record from _build_record().
        path : str, optional
            Override the file path from CONFIG.  Useful for testing.
        """
        target_path = path or self.config.get("log_file_path", "crm_activity.jsonl")

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

        try:
            with open(target_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            logger.debug("CRM log written to file: %s", target_path)
        except OSError as exc:
            logger.error("Failed to write CRM log to file %s: %s", target_path, exc)
            raise

    # ── CRM write-back stub ──────────────────────────────────────────────────

    def log_to_crm(self, record: dict) -> None:
        """
        Write a log record back to the CRM system.

        STUB — raises NotImplementedError until a CRM integration is
        configured.  Implement this method when a CRM SDK or API client
        is available.

        Integration guide:
            1. Import the CRM client SDK (e.g. Salesforce simple_salesforce,
               Dynamics 365 via msal + requests, or an internal wrapper).
            2. Authenticate using credentials from environment variables:
                   CRM_CLIENT_ID, CRM_CLIENT_SECRET, CRM_INSTANCE_URL
            3. Map `record` fields to CRM object fields:
                   record["client_id"]       → Contact/Account external ID
                   record["content_summary"] → Activity Description
                   record["timestamp"]       → ActivityDate
                   record["rm_user"]         → OwnerId
                   record["tags"]            → Custom Tag field (multi-select)
            4. POST to the CRM activity/notes endpoint.
            5. Log the CRM-assigned activity ID for audit purposes.

        Parameters
        ----------
        record : dict
            Structured log record from _build_record().
        """
        # EXTENSION POINT: replace this block with your CRM client call
        raise NotImplementedError(
            "log_to_crm() is not yet implemented. "
            "See the integration guide in the docstring for instructions."
        )

    # ── REST API write-back stub ─────────────────────────────────────────────

    def log_to_api(self, record: dict, endpoint: Optional[str] = None) -> None:
        """
        POST a log record to an internal REST API endpoint.

        STUB — raises NotImplementedError until an endpoint is confirmed.

        Integration guide:
            1. Configure the target endpoint via environment variable:
                   AUREUS_LOG_API_ENDPOINT=https://internal.api.example.com/v1/rm-events
            2. Authenticate with a bearer token:
                   AUREUS_LOG_API_TOKEN=<service-account-token>
            3. Use `requests` (or httpx for async) to POST the record:
                   import requests
                   resp = requests.post(
                       endpoint,
                       json=record,
                       headers={"Authorization": f"Bearer {token}"},
                       timeout=5,
                   )
                   resp.raise_for_status()
            4. Handle retries with exponential backoff for transient failures.
            5. Log the API-assigned event ID returned in the response body.

        Parameters
        ----------
        record : dict
            Structured log record from _build_record().
        endpoint : str, optional
            Override the API endpoint URL from environment config.
        """
        # EXTENSION POINT: replace this block with your HTTP client call
        raise NotImplementedError(
            "log_to_api() is not yet implemented. "
            "See the integration guide in the docstring for instructions."
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC DISPATCH FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def dispatch_log(
    command: str,
    client_id: Optional[str],
    response_text: str,
    metadata: dict,
    config_override: Optional[dict] = None,
) -> dict:
    """
    Build a structured log record and route it to all enabled destinations.

    This is the primary entry point for the CRM logger hook.  Call it from
    any command handler that should leave an activity trail.

    Parameters
    ----------
    command : str
        Command slug that generated this response (e.g. "meeting-pack").
    client_id : str | None
        CRM client identifier.  May be None for non-client-specific commands.
    response_text : str
        The full response text generated for this command.
    metadata : dict
        Supplementary context.  Recognised keys:
            rm_user       (str)   RM user identifier / email.
            model_version (str)   Claude model version string.
            session_id    (str)   Conversation / session identifier.
            latency_ms    (int)   Response generation latency in milliseconds.
            data_sources  (list)  MCP tools / data sources used.
            tags          (list)  Additional string tags.
    config_override : dict, optional
        Override specific CONFIG keys for this call (useful in tests).

    Returns
    -------
    dict
        {
          "dispatched"  : bool,          # False if disabled or command not in log_commands
          "record"      : dict | None,   # The log record that was built
          "destinations": list[str],     # Destinations that were attempted
          "errors"      : list[str],     # Any non-fatal dispatch errors
        }
    """
    cfg = {**CONFIG, **(config_override or {})}
    dispatcher = LogDispatcher(config=cfg)

    # ── Guard: logging disabled globally ────────────────────────────────────
    if not cfg.get("enabled"):
        logger.debug("CRM logging disabled globally — skipping for command=%s", command)
        return {"dispatched": False, "record": None, "destinations": [], "errors": []}

    # ── Guard: command not in the watch-list ─────────────────────────────────
    log_commands = cfg.get("log_commands", [])
    if log_commands and command not in log_commands:
        logger.debug(
            "Command '%s' not in log_commands list — skipping CRM log.", command
        )
        return {"dispatched": False, "record": None, "destinations": [], "errors": []}

    # ── Build the record ─────────────────────────────────────────────────────
    record = _build_record(command, client_id, response_text, metadata)

    destinations: list[str] = []
    errors: list[str] = []

    # ── Dispatch to file ─────────────────────────────────────────────────────
    if cfg.get("log_to_file"):
        try:
            dispatcher.log_to_file(record)
            destinations.append("file")
        except Exception as exc:
            msg = f"log_to_file failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    # ── Dispatch to CRM ──────────────────────────────────────────────────────
    if cfg.get("log_to_crm"):
        try:
            dispatcher.log_to_crm(record)
            destinations.append("crm")
        except NotImplementedError:
            msg = "log_to_crm is a stub — not yet implemented."
            logger.warning(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"log_to_crm failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    # ── Dispatch to API ──────────────────────────────────────────────────────
    if cfg.get("log_to_api"):
        try:
            dispatcher.log_to_api(record)
            destinations.append("api")
        except NotImplementedError:
            msg = "log_to_api is a stub — not yet implemented."
            logger.warning(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"log_to_api failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    logger.info(
        "CRM log dispatched | command=%s client_id=%s destinations=%s errors=%d",
        command,
        client_id,
        destinations,
        len(errors),
    )

    return {
        "dispatched": True,
        "record": record,
        "destinations": destinations,
        "errors": errors,
    }
