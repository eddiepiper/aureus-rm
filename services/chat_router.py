"""
services/chat_router.py

Natural-language intent detection and multi-turn conversation state for Aureus.

Flow:
  1. Receive free-text message from Telegram
  2. Detect intent with deterministic keyword rules
  3. If args are missing, check session state (RelationshipMemoryService) for last client/ticker
  4. If still missing, ask a clarifying question and save pending state
  5. Once intent + args are resolved, delegate to CommandRouter

Session continuity:
  - ConversationState owns 1-step clarification state (waiting_for = "client_name" | "ticker")
  - RelationshipMemoryService owns persistent session state (last_client, last_ticker, last_intent)
  - ChatRouter reads session state for context-aware fallbacks ("What about DBS?" after John Tan context)
  - Session state is updated by CommandRouter after each successful command — never by ChatRouter
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------

INTENTS: dict[str, list[str]] = {
    # V2
    "client_review": [
        "client review", "review client", "review for", "review ",
        "how is", "tell me about", "client summary", "show me", "pull up",
        "what's happening with", "whats happening with",
    ],
    "meeting_pack": [
        "meeting pack", "meeting prep", "prepare meeting", "prep for",
        "meeting with", "getting ready for", "before i meet",
    ],
    "next_best_action": [
        "next best action", "next action", "what should i do",
        "what to do", "nba", "recommend", "suggestions for",
        "follow up", "followup", "action items",
    ],
    "portfolio_fit": [
        "portfolio fit", "fit for", "add to portfolio", "should i add",
        "suitable for", "concentration", "would it fit", "does ", " fit",
    ],
    # V3 Equity
    "earnings_deep_dive": [
        "earnings", "results", "quarterly results", "earnings deep dive",
        "how did", "how did it do", "beat", "miss", "guidance",
    ],
    "stock_catalyst": [
        "catalyst", "catalysts", "what's driving", "whats driving",
        "what could move", "near term", "upcoming", "what to watch",
    ],
    "thesis_check": [
        "thesis", "bull case", "bear case", "investment case",
        "why own", "why hold", "conviction", "view on",
    ],
    "idea_generation": [
        "ideas for", "stock ideas", "what should i look at",
        "what fits", "suggest something for",
        "what would work for", "any ideas",
    ],
    "morning_note": [
        "morning note", "morning update",
        "what to know about", "quick brief on", "brief on",
    ],
    # V3 Wealth
    "portfolio_scenario": [
        "scenario", "portfolio scenario", "stress test",
        "what if", "downside scenario", "risk scenario",
        "portfolio risk", "what happens if",
    ],
    # V5.1 — Relationship Memory + NBA
    "relationship_status": [
        "relationship status", "how is my relationship with",
        "status with", "status for", "relationship with",
        "how are things with", "what's the relationship",
    ],
    "overdue_followups": [
        "overdue", "what's overdue", "whats overdue",
        "anything overdue", "any overdue for", "overdue for",
        "what's outstanding", "whats outstanding",
    ],
    "attention_list": [
        "attention list", "who needs attention", "priority clients",
        "who should i focus", "who should i call", "who to focus",
        "who to contact", "which clients",
    ],
    "morning_rm_brief": [
        "morning brief", "daily brief", "what should i focus on today",
        "focus today", "what to do today", "start of day",
        "rm brief", "daily rundown",
    ],
    "log_response": [
        "log response", "client said", "client is interested",
        "client declined", "client neutral", "mark as interested",
        "mark as declined", "record response", "log client",
    ],
    # Help
    "help": [
        "help", "what can you do", "commands", "how do i",
        "what are your commands", "options",
    ],
}

HELP_TEXT = (
    "*Aureus RM Copilot* — what I can do:\n\n"
    "*V2 Client & Portfolio:*\n"
    "- *Client Review* — `review John Tan`\n"
    "- *Meeting Pack* — `meeting pack for John Tan`\n"
    "- *Next Best Actions* — `what should I do for John Tan`\n"
    "- *Portfolio Fit* — `does DBS fit John Tan`\n\n"
    "*V3 Equity Research:*\n"
    "- *Earnings* — `how did NVDA do this quarter`\n"
    "- *Catalyst* — `what's driving TSM`\n"
    "- *Thesis* — `bull case for AAPL`\n"
    "- *Ideas* — `any ideas for John Tan`\n"
    "- *Morning Note* — `brief on DBS`\n"
    "- *Portfolio Scenario* — `stress test John Tan's portfolio`\n\n"
    "*V5.1 Relationship Memory & NBA:*\n"
    "- *Relationship Status* — `relationship status for John Tan`\n"
    "- *Overdue Follow-Ups* — `anything overdue for John Tan`\n"
    "- *Attention List* — `who needs attention today`\n"
    "- *Morning RM Brief* — `what should I focus on today`\n"
    "- *Log Client Response* — `log response John Tan interested NVDA`\n\n"
    "Or use slash commands — type /help."
)

# Ticker pattern: 1-5 uppercase letters optionally followed by .XX exchange suffix
TICKER_RE = re.compile(r"\b([A-Z]{1,5}(?:\.[A-Z]{2})?)\b")

NOT_TICKERS = {
    "I", "A", "THE", "FOR", "AND", "OR", "IS", "IT", "IN", "TO",
    "MY", "ME", "HIS", "HER", "DID", "DO", "BE", "AM", "ARE",
    "CAN", "DOES", "CEO", "CFO", "COO", "RM", "AUM", "NBA",
    "SGD", "USD", "HKD", "EUR", "GBP",
    "HOW", "WHAT", "WHY", "WHO", "ANY", "ALL", "NEW", "OLD",
    "BUY", "SELL", "OWN", "RUN", "GET", "LET", "PUT", "USE",
    "HAS", "HAD", "WAS", "NOT", "BUT", "YET", "NOW", "ON",
    "UP", "AT", "BY", "IF", "OF", "SO", "AS",
    "BULL", "BEAR", "CASE", "VIEW", "MISS", "BEAT",
    "NEAR", "TERM", "NEXT", "LAST", "THIS",
    "JOHN", "TAN", "QUICK", "BRIEF", "WHAT'S",
}

# ---------------------------------------------------------------------------
# Intent → command slug mapping
# ---------------------------------------------------------------------------

_COMMAND_MAP: dict[str, str] = {
    # V2
    "client_review":      "client-review",
    "meeting_pack":       "meeting-pack",
    "next_best_action":   "next-best-action",
    "portfolio_fit":      "portfolio-fit",
    # V3
    "earnings_deep_dive": "earnings-deep-dive",
    "stock_catalyst":     "stock-catalyst",
    "thesis_check":       "thesis-check",
    "idea_generation":    "idea-generation",
    "morning_note":       "morning-note",
    "portfolio_scenario": "portfolio-scenario",
    # V5.1
    "relationship_status": "relationship-status",
    "overdue_followups":   "overdue-followups",
    "attention_list":      "attention-list",
    "morning_rm_brief":    "morning-rm-brief",
    "log_response":        "log-response",
}

_TICKER_COMMANDS = frozenset({
    "earnings_deep_dive", "stock_catalyst", "thesis_check", "morning_note",
})

_CLIENT_COMMANDS_V3 = frozenset({
    "idea_generation", "portfolio_scenario",
})

_CLIENT_COMMANDS_V2 = frozenset({
    "client_review", "meeting_pack", "next_best_action",
    "relationship_status", "overdue_followups",
})

# Commands that need neither a client nor a ticker
_NO_ARG_COMMANDS = frozenset({
    "attention_list", "morning_rm_brief",
})


# ---------------------------------------------------------------------------
# In-memory clarification state  {chat_id: ConversationState}
# ---------------------------------------------------------------------------

class ConversationState:
    """Tracks the current pending clarification for a single chat_id."""

    def __init__(self):
        self.intent: Optional[str] = None
        self.client_name: Optional[str] = None
        self.ticker: Optional[str] = None
        self.waiting_for: Optional[str] = None  # "client_name" | "ticker"
        self.response_status: Optional[str] = None  # for log-response

    def reset(self):
        self.intent = None
        self.client_name = None
        self.ticker = None
        self.waiting_for = None
        self.response_status = None

    def is_pending(self) -> bool:
        return self.intent is not None and self.waiting_for is not None


# ---------------------------------------------------------------------------
# ChatRouter class
# ---------------------------------------------------------------------------

class ChatRouter:
    """
    Natural-language router for Aureus Telegram messages.

    Owns 1-step clarification state per chat_id.
    Reads RelationshipMemoryService for session continuity (last client/ticker).
    Session state is never written here — only by CommandRouter after success.
    """

    def __init__(self, relationship_memory=None):
        self._relationship_memory = relationship_memory
        self._states: dict[str, ConversationState] = {}

    def _get_state(self, chat_id: str) -> ConversationState:
        if chat_id not in self._states:
            self._states[chat_id] = ConversationState()
        return self._states[chat_id]

    def clear_state(self, chat_id: str) -> None:
        if chat_id in self._states:
            self._states[chat_id].reset()

    def _get_session_client(self, chat_id: str) -> Optional[str]:
        """Return last known client name from session state."""
        if not self._relationship_memory:
            return None
        session = self._relationship_memory.get_session_state(chat_id)
        return session.get("last_client_name")

    def _get_session_ticker(self, chat_id: str) -> Optional[str]:
        """Return last known ticker from session state."""
        if not self._relationship_memory:
            return None
        session = self._relationship_memory.get_session_state(chat_id)
        return session.get("last_ticker")

    def resolve(self, chat_id: str, text: str) -> "ChatResolution":
        """
        Given a raw Telegram message, return either:
          - ChatResolution(command=..., args=...) — delegate to CommandRouter
          - ChatResolution(reply=...) — send a clarifying question back
        """
        state = self._get_state(chat_id)
        stripped = text.strip()

        # -----------------------------------------------------------------------
        # Handle pending state — user is answering a clarifying question
        # -----------------------------------------------------------------------
        if state.is_pending():
            if state.waiting_for == "client_name":
                state.client_name = stripped.title()
                state.waiting_for = None
                if state.intent == "portfolio_fit" and not state.ticker:
                    state.waiting_for = "ticker"
                    return ChatResolution(
                        reply=f"Got it — *{state.client_name}*. Which ticker are you looking at?"
                    )
            elif state.waiting_for == "ticker":
                ticker = _extract_ticker(stripped.upper()) or stripped.upper().strip()
                state.ticker = ticker
                state.waiting_for = None

            if not state.waiting_for:
                return self._build_resolution(state, chat_id)

        # -----------------------------------------------------------------------
        # Fresh message — detect intent
        # -----------------------------------------------------------------------
        intent = _detect_intent(stripped)

        if intent is None:
            state.reset()
            return ChatResolution(
                reply=(
                    "I didn't quite catch that. Try:\n\n"
                    "- `review John Tan`\n"
                    "- `meeting pack for John Tan`\n"
                    "- `next best action for John Tan`\n"
                    "- `relationship status for John Tan`\n"
                    "- `who needs attention today`\n"
                    "- `what should I focus on today`\n\n"
                    "Or type /help."
                )
            )

        if intent == "help":
            state.reset()
            return ChatResolution(reply=HELP_TEXT)

        state.intent = intent
        state.waiting_for = None

        # No-arg commands (attention-list, morning-rm-brief)
        if intent in _NO_ARG_COMMANDS:
            state.client_name = None
            state.ticker = None
            return self._build_resolution(state, chat_id)

        # Ticker commands
        if intent in _TICKER_COMMANDS:
            state.client_name = None
            state.ticker = _extract_ticker(stripped)
            # Session continuity: fall back to last known ticker
            if not state.ticker:
                state.ticker = self._get_session_ticker(chat_id)
            if not state.ticker:
                state.waiting_for = "ticker"
                prompts = {
                    "earnings_deep_dive": "Which ticker would you like an earnings deep dive on?",
                    "stock_catalyst":     "Which ticker are you looking at for catalysts?",
                    "thesis_check":       "Which ticker should I check the thesis for?",
                    "morning_note":       "Which ticker or sector would you like a morning note on?",
                }
                return ChatResolution(reply=prompts.get(intent, "Which ticker?"))

        # log_response: needs client + response status
        elif intent == "log_response":
            state.client_name = _extract_client_name(stripped, intent)
            if not state.client_name:
                state.client_name = self._get_session_client(chat_id)
            if not state.client_name:
                state.waiting_for = "client_name"
                return ChatResolution(
                    reply="Which client did you speak with? (e.g. `John Tan interested NVDA`)"
                )

        # V3 client commands
        elif intent in _CLIENT_COMMANDS_V3:
            state.ticker = None
            state.client_name = _extract_client_name(stripped, intent)
            if not state.client_name:
                state.client_name = self._get_session_client(chat_id)
            if not state.client_name:
                state.waiting_for = "client_name"
                prompts = {
                    "idea_generation":    "Which client should I generate ideas for?",
                    "portfolio_scenario": "Which client's portfolio should I run scenarios on?",
                }
                return ChatResolution(reply=prompts.get(intent, "Which client?"))

        # V2 + V5.1 client commands
        else:
            state.client_name = _extract_client_name(stripped, intent)
            state.ticker = (
                _extract_ticker(stripped) if intent == "portfolio_fit" else None
            )
            # Session continuity: use last known client if none extracted
            if not state.client_name:
                state.client_name = self._get_session_client(chat_id)
            if not state.client_name:
                state.waiting_for = "client_name"
                prompts = {
                    "client_review":      "Sure — which client would you like a review for?",
                    "meeting_pack":       "Happy to help prep. Which client is the meeting for?",
                    "next_best_action":   "Which client should I suggest next actions for?",
                    "portfolio_fit":      "Which client are you assessing?",
                    "relationship_status": "Which client's relationship status would you like?",
                    "overdue_followups":  "Which client should I check for overdue items?",
                }
                return ChatResolution(reply=prompts.get(intent, "Which client?"))
            if intent == "portfolio_fit" and not state.ticker:
                state.waiting_for = "ticker"
                return ChatResolution(
                    reply=f"Got it — *{state.client_name}*. Which ticker are you looking at?"
                )

        return self._build_resolution(state, chat_id)

    def _build_resolution(self, state: ConversationState, chat_id: str) -> "ChatResolution":
        """Map resolved intent + args to a command_router command."""
        command = _COMMAND_MAP[state.intent]

        if state.intent in _TICKER_COMMANDS:
            args = [state.ticker] if state.ticker else []
        elif state.intent in _NO_ARG_COMMANDS:
            args = []
        elif state.intent == "portfolio_fit":
            args = state.client_name.split() if state.client_name else []
            if state.ticker:
                args = args + [state.ticker]
        elif state.intent == "log_response":
            # Pass as: [client_words...] [status] [optional_ticker]
            args = state.client_name.split() if state.client_name else []
            if state.response_status:
                args = args + [state.response_status]
            if state.ticker:
                args = args + [state.ticker]
        else:
            args = state.client_name.split() if state.client_name else []

        logger.info(
            "ChatRouter resolved | chat_id=%s intent=%s client=%s ticker=%s",
            chat_id, state.intent, state.client_name, state.ticker,
        )

        state.reset()
        return ChatResolution(command=command, args=args)


# ---------------------------------------------------------------------------
# ChatResolution
# ---------------------------------------------------------------------------

class ChatResolution:
    """Result returned by ChatRouter.resolve(). Either a command or a question."""

    def __init__(
        self,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        reply: Optional[str] = None,
    ):
        self.command = command
        self.args = args or []
        self.reply = reply

    @property
    def ready(self) -> bool:
        return self.command is not None


# ---------------------------------------------------------------------------
# Module-level helper functions (used internally)
# ---------------------------------------------------------------------------

def _detect_intent(text: str) -> Optional[str]:
    lower = text.lower()
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in lower:
                return intent
    return None


def _extract_ticker(text: str) -> Optional[str]:
    matches = TICKER_RE.findall(text.upper())
    for m in matches:
        if m not in NOT_TICKERS and len(m) >= 2:
            return m
    return None


_COMMON_WORDS = {
    "what", "is", "are", "was", "were", "do", "does", "did",
    "how", "why", "who", "when", "where", "which",
    "any", "all", "any", "some", "this", "that", "these", "those",
    "can", "could", "would", "should", "will", "shall", "may", "might",
    "its", "it", "he", "she", "we", "they", "you", "me", "him", "her", "us", "them",
    "my", "your", "his", "her", "our", "their", "its",
    "yes", "no", "not", "but", "and", "or", "so", "yet", "nor",
    "get", "give", "got", "let", "put", "run", "see", "set", "use",
    "has", "had", "have", "been", "be", "am",
    "into", "from", "out", "up", "down", "over", "under", "back",
    "more", "less", "most", "least", "very", "much", "many",
    "also", "just", "still", "already", "now", "then", "here", "there",
    "look", "show", "tell", "know", "think", "want", "need",
    "check", "find", "go", "come", "take",
    "anything", "something", "nothing", "everything", "someone", "anyone",
    "right", "ok", "okay", "sure", "please", "thanks", "thank",
}


def _extract_client_name(text: str, intent: str) -> Optional[str]:
    """
    Heuristic: strip intent keywords and connector words, treat remainder as client name.
    Requires at least 2 words or 1 capitalised word.
    Filters out common English words to avoid false positives.
    """
    # Work on a clean copy without tickers
    clean = TICKER_RE.sub("", text).strip()

    # Strip intent keywords
    for kw in INTENTS.get(intent, []):
        clean = re.sub(re.escape(kw), "", clean, flags=re.IGNORECASE).strip()

    # Strip common connectors
    for word in ["for", "of", "about", "with", "client", "the", "a",
                 "on", "in", "at", "'s", "portfolio", "today", "me", "us"]:
        clean = re.sub(rf"\b{re.escape(word)}\b", "", clean, flags=re.IGNORECASE).strip()

    clean = clean.strip(" ,.-?'")

    # Filter out common English words — only keep candidate name words
    words = [
        w for w in clean.split()
        if len(w) > 1 and w.lower() not in _COMMON_WORDS
    ]
    if len(words) >= 2:
        return " ".join(w.title() for w in words)
    if len(words) == 1 and words[0][0].isupper():
        return words[0]
    return None


# ---------------------------------------------------------------------------
# Module-level backward-compatible resolve() for existing callers
# ---------------------------------------------------------------------------

_default_router: Optional[ChatRouter] = None


def _get_default_router() -> ChatRouter:
    global _default_router
    if _default_router is None:
        _default_router = ChatRouter()
    return _default_router


def resolve(chat_id: str, text: str) -> ChatResolution:
    """
    Module-level backward-compatible resolve().
    Prefer using ChatRouter instances injected via dependency injection.
    """
    return _get_default_router().resolve(chat_id, text)


def clear_state(chat_id: str) -> None:
    _get_default_router().clear_state(chat_id)
