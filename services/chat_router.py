"""
services/chat_router.py

Natural-language intent detection and multi-turn conversation state for Aureus.

Flow:
  1. Receive free-text message from Telegram
  2. Detect intent with deterministic keyword rules
  3. If args are missing, ask a clarifying question and save state
  4. Once intent + args are resolved, delegate to CommandRouter

State is stored in memory per chat_id. Resets after a successful command
or after the user starts a new unrelated message.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------

INTENTS = {
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
    "help": [
        "help", "what can you do", "commands", "how do i",
        "what are your commands", "options",
    ],
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
        "morning note", "morning brief", "morning update",
        "what to know about", "quick brief on", "brief on",
    ],
    "portfolio_scenario": [
        "scenario", "portfolio scenario", "stress test",
        "what if", "downside scenario", "risk scenario",
        "portfolio risk", "what happens if",
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
    "- *Morning Note* — `morning brief on DBS`\n"
    "- *Portfolio Scenario* — `stress test John Tan's portfolio`\n\n"
    "Or use slash commands — type /help."
)

# Ticker pattern: 1-5 uppercase letters optionally followed by .XX exchange suffix
TICKER_RE = re.compile(r"\b([A-Z]{1,5}(?:\.[A-Z]{2})?)\b")

# Common words to exclude from ticker detection
NOT_TICKERS = {
    "I", "A", "THE", "FOR", "AND", "OR", "IS", "IT", "IN", "TO",
    "MY", "ME", "HIS", "HER", "DID", "DO", "BE", "AM", "ARE",
    "CAN", "DOES", "CEO", "CFO", "COO", "RM", "AUM", "NBA",
    "SGD", "USD", "HKD", "EUR", "GBP",
    # Common sentence words that match ticker pattern
    "HOW", "WHAT", "WHY", "WHO", "ANY", "ALL", "NEW", "OLD",
    "BUY", "SELL", "OWN", "RUN", "GET", "LET", "PUT", "USE",
    "HAS", "HAD", "WAS", "NOT", "BUT", "YET", "NOW", "ON",
    "UP", "AT", "BY", "IF", "OF", "SO", "AS",
    "BULL", "BEAR", "CASE", "VIEW", "MISS", "BEAT",
    "NEAR", "TERM", "NEXT", "LAST", "THIS",
    "JOHN", "TAN", "QUICK", "BRIEF", "WHAT'S",
}


# ---------------------------------------------------------------------------
# In-memory conversation state  {chat_id: ConversationState}
# ---------------------------------------------------------------------------

class ConversationState:
    def __init__(self):
        self.intent: Optional[str] = None
        self.client_name: Optional[str] = None
        self.ticker: Optional[str] = None
        self.waiting_for: Optional[str] = None  # "client_name" | "ticker"

    def reset(self):
        self.intent = None
        self.client_name = None
        self.ticker = None
        self.waiting_for = None

    def is_pending(self) -> bool:
        return self.intent is not None and self.waiting_for is not None


_states: dict[str, ConversationState] = {}


def _get_state(chat_id: str) -> ConversationState:
    if chat_id not in _states:
        _states[chat_id] = ConversationState()
    return _states[chat_id]


def clear_state(chat_id: str):
    if chat_id in _states:
        _states[chat_id].reset()


# ---------------------------------------------------------------------------
# Intent detection helpers
# ---------------------------------------------------------------------------

def _detect_intent(text: str) -> Optional[str]:
    lower = text.lower()
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in lower:
                return intent
    return None


def _extract_ticker(text: str) -> Optional[str]:
    """Extract a likely ticker symbol from text."""
    matches = TICKER_RE.findall(text.upper())
    for m in matches:
        if m not in NOT_TICKERS and len(m) >= 2:
            return m
    return None


def _extract_client_name(text: str, intent: str) -> Optional[str]:
    """
    Heuristic: strip intent keywords from the message and treat the remainder
    as a potential client name. Requires at least 2 words.
    """
    lower = text.lower().strip()

    # Strip intent keywords
    for kw in INTENTS.get(intent, []):
        lower = lower.replace(kw, "").strip()

    # Strip common connector words
    for word in ["for", "of", "about", "with", "client", "the", "a"]:
        lower = re.sub(rf"\b{word}\b", "", lower).strip()

    # Strip tickers
    clean = TICKER_RE.sub("", text).strip()
    for kw in INTENTS.get(intent, []):
        clean = re.sub(re.escape(kw), "", clean, flags=re.IGNORECASE).strip()
    for word in ["for", "of", "about", "with", "client", "the", "a"]:
        clean = re.sub(rf"\b{word}\b", "", clean, flags=re.IGNORECASE).strip()
    clean = clean.strip(" ,.-?")

    # Title-case what's left — likely a name if 2+ words or capitalised
    words = [w for w in clean.split() if len(w) > 1]
    if len(words) >= 2:
        return " ".join(w.title() for w in words)
    if len(words) == 1 and words[0][0].isupper():
        return words[0]
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class ChatResolution:
    """Result returned by resolve(). Either a command to run or a question to ask."""

    def __init__(
        self,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        reply: Optional[str] = None,
    ):
        self.command = command      # set if ready to execute
        self.args = args or []      # args for command_router
        self.reply = reply          # set if we need to ask the user something

    @property
    def ready(self) -> bool:
        return self.command is not None


def resolve(chat_id: str, text: str) -> ChatResolution:
    """
    Given a raw Telegram message, return either:
      - A ready command + args (delegate to CommandRouter)
      - A reply string (ask a clarifying question or return help)
    """
    state = _get_state(chat_id)
    stripped = text.strip()

    # -----------------------------------------------------------------------
    # Handle pending state — user is answering a clarifying question
    # -----------------------------------------------------------------------
    if state.is_pending():
        if state.waiting_for == "client_name":
            # The whole message is the client name
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

        # Check if we're now ready
        if not state.waiting_for:
            return _build_resolution(state, chat_id)

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
                "- `does DBS fit John Tan`\n\n"
                "Or type /help."
            )
        )

    if intent == "help":
        state.reset()
        return ChatResolution(reply=HELP_TEXT)

    state.intent = intent
    state.waiting_for = None

    TICKER_COMMANDS = {"earnings_deep_dive", "stock_catalyst", "thesis_check", "morning_note"}
    CLIENT_COMMANDS_V3 = {"idea_generation", "portfolio_scenario"}

    if intent in TICKER_COMMANDS:
        state.ticker = _extract_ticker(stripped)
        state.client_name = None
        if not state.ticker:
            state.waiting_for = "ticker"
            prompts = {
                "earnings_deep_dive": "Which ticker would you like an earnings deep dive on?",
                "stock_catalyst":     "Which ticker are you looking at for catalysts?",
                "thesis_check":       "Which ticker should I check the thesis for?",
                "morning_note":       "Which ticker or sector would you like a morning note on?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which ticker?"))
    elif intent in CLIENT_COMMANDS_V3:
        state.ticker = None
        state.client_name = _extract_client_name(stripped, intent)
        if not state.client_name:
            state.waiting_for = "client_name"
            prompts = {
                "idea_generation":    "Which client should I generate ideas for?",
                "portfolio_scenario": "Which client's portfolio should I run scenarios on?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which client?"))
    else:
        # V2 intents — original logic preserved exactly
        state.client_name = _extract_client_name(stripped, intent)
        state.ticker = _extract_ticker(stripped) if intent == "portfolio_fit" else None
        if not state.client_name:
            state.waiting_for = "client_name"
            prompts = {
                "client_review":    "Sure — which client would you like a review for?",
                "meeting_pack":     "Happy to help prep. Which client is the meeting for?",
                "next_best_action": "Which client should I suggest next actions for?",
                "portfolio_fit":    "Which client are you assessing?",
            }
            return ChatResolution(reply=prompts.get(intent, "Which client?"))
        if intent == "portfolio_fit" and not state.ticker:
            state.waiting_for = "ticker"
            return ChatResolution(
                reply=f"Got it — *{state.client_name}*. Which ticker are you looking at?"
            )

    return _build_resolution(state, chat_id)


def _build_resolution(state: ConversationState, chat_id: str) -> ChatResolution:
    """Map resolved intent + args to a command_router command."""
    command_map = {
        # V2
        "client_review":    "client-review",
        "meeting_pack":     "meeting-pack",
        "next_best_action": "next-best-action",
        "portfolio_fit":    "portfolio-fit",
        # V3
        "earnings_deep_dive": "earnings-deep-dive",
        "stock_catalyst":     "stock-catalyst",
        "thesis_check":       "thesis-check",
        "idea_generation":    "idea-generation",
        "morning_note":       "morning-note",
        "portfolio_scenario": "portfolio-scenario",
    }
    command = command_map[state.intent]

    TICKER_COMMANDS = {"earnings_deep_dive", "stock_catalyst", "thesis_check", "morning_note"}
    if state.intent in TICKER_COMMANDS:
        args = [state.ticker] if state.ticker else []
    else:
        args = state.client_name.split() if state.client_name else []
        if state.intent == "portfolio_fit" and state.ticker:
            args = args + [state.ticker]

    logger.info(
        "ChatRouter resolved | chat_id=%s intent=%s client=%s ticker=%s",
        chat_id, state.intent, state.client_name, state.ticker,
    )

    state.reset()
    return ChatResolution(command=command, args=args)
