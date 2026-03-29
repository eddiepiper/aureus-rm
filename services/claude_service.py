"""
services/claude_service.py

Claude API wrapper for Aureus RM Copilot.

Builds structured prompts from client context data and skills files,
then calls the Claude API to generate RM-quality responses.

Used by: command_router.py (Telegram bot path)
Not used for: Claude Code CLI commands (those use .mcp.json + skills directly)
"""

import json
import logging
from pathlib import Path
from typing import Optional

import anthropic
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"

# Which skills to load for each command
COMMAND_SKILLS: dict[str, list[str]] = {
    "client-review": [
        "rm-client-meeting-prep",
        "suitability-response-style",
        "output-formatting-rules",
    ],
    "portfolio-fit": [
        "portfolio-concentration-check",
        "suitability-response-style",
        "output-formatting-rules",
    ],
    "meeting-pack": [
        "rm-client-meeting-prep",
        "suitability-response-style",
        "output-formatting-rules",
    ],
    "next-best-action": [
        "next-best-action-framework",
        "suitability-response-style",
        "output-formatting-rules",
    ],
}

# Telegram-specific formatting instructions appended to every system prompt
TELEGRAM_FORMAT_INSTRUCTIONS = """
## Output Formatting for Telegram

Your response will be sent via Telegram. Follow these rules exactly:
- Use *bold* for section headers and key labels (single asterisk each side)
- Use _italic_ for disclaimers and notes (single underscore each side)
- Use - for bullet points
- Keep each section concise — 3 to 6 bullets maximum
- Do not use markdown headers (#, ##, ###) — they do not render in Telegram
- Do not use tables — they do not render properly in Telegram
- Total response should be under 3000 characters where possible
- Separate sections with a blank line
- End every response with the disclaimer:
  _This output is for internal RM use only and does not constitute investment advice._
"""

# Per-command user prompt templates
COMMAND_PROMPTS: dict[str, str] = {
    "client-review": """
Generate a client review for *{client_name}* based on the data below.

Include these sections:
- *Profile* — segment, risk, objective, horizon
- *Portfolio* — top holdings with weight and P&L, concentration observations
- *Recent Interactions* — last 3, note any pending follow-ups
- *Open Actions* — open tasks from the system
- *Suggested Talking Points* — 3 to 5 points based on the data

Client data:
{context_json}
""",
    "portfolio-fit": """
Assess whether *{ticker}* is a suitable addition to *{client_name}*'s portfolio.

Include these sections:
- *Client Mandate* — key constraints and risk profile
- *Current Exposure* — relevant sector and geography weights
- *Concentration Impact* — what adding this ticker would do
- *Fit Assessment* — Fits / Partially Fits / Does Not Fit, with rationale
- *Risks to Discuss* — 2 to 3 risks specific to this client
- *Suitability Framing* — one sentence the RM can use

Note: Live market data is not available in this context. Base assessment on portfolio
data and client mandate only. State this limitation clearly.

Client and portfolio data:
{context_json}
""",
    "meeting-pack": """
Prepare a meeting pack for *{client_name}*.

Include these sections:
- *Client Summary* — key profile facts in 2 to 3 lines
- *Portfolio Overview* — top 5 holdings, concentration note
- *Since Last Meeting* — notable changes or pending items from interactions
- *Discussion Topics* — 3 to 5 topics with brief context
- *Suggested Agenda* — 4 to 5 agenda items with estimated time
- *Open Follow-ups* — outstanding items from prior meetings

Client data:
{context_json}
""",
    "next-best-action": """
Suggest next best actions for the RM managing *{client_name}*.

For each action (aim for 3 to 5):
- *[Priority] Action title*
- What: specific action
- Why: rationale tied to client data
- Timing: when to act

Base actions on the client's portfolio state, open tasks, and interaction history.
Each action must be executable by an RM — not generic advice.

Client data:
{context_json}
""",
}


class ClaudeService:
    """
    Wraps the Anthropic API for Aureus command generation.

    Args:
        api_key: Anthropic API key
        model:   Claude model to use (default: claude-sonnet-4-6)
        max_tokens: max tokens per response
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
    ):
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self._skill_cache: dict[str, str] = {}

    def _load_skill(self, skill_name: str, max_chars: int = 1500) -> str:
        """
        Load a skill file from disk, truncated to max_chars to keep prompts fast.
        Caches on first read.
        """
        if skill_name in self._skill_cache:
            return self._skill_cache[skill_name]

        skill_path = SKILLS_DIR / f"{skill_name}.md"
        if not skill_path.exists():
            logger.warning("Skill file not found: %s", skill_path)
            return ""

        content = skill_path.read_text(encoding="utf-8")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... [truncated for speed]"
        self._skill_cache[skill_name] = content
        return content

    def _build_system_prompt(self, command: str) -> str:
        """
        Assemble the system prompt for a command:
          1. Role definition
          2. Relevant skill files
          3. Telegram formatting instructions
        """
        skills = COMMAND_SKILLS.get(command, ["suitability-response-style"])
        skill_blocks = []
        for skill_name in skills:
            content = self._load_skill(skill_name)
            if content:
                skill_blocks.append(f"--- Skill: {skill_name} ---\n{content}")

        system = (
            "You are Aureus, an AI copilot for bank relationship managers. "
            "You help RMs prepare for client meetings, review portfolios, and plan next actions. "
            "You are NOT a trading system. You do NOT give investment advice. "
            "You provide structured, compliance-aware decision support for internal RM use only.\n\n"
        )

        if skill_blocks:
            system += "## Applied Skills and Guidelines\n\n"
            system += "\n\n".join(skill_blocks)
            system += "\n\n"

        system += TELEGRAM_FORMAT_INSTRUCTIONS
        return system

    def _build_user_prompt(self, command: str, ctx: dict) -> str:
        """Build the user prompt from the command template and context data."""
        template = COMMAND_PROMPTS.get(command)
        if not template:
            return f"Run the {command} command for this client context:\n{json.dumps(ctx, indent=2, default=str)}"

        client_name = ctx.get("customer", {}).get("preferred_name") or ctx.get("customer", {}).get("full_name", "Unknown")
        ticker = ctx.get("ticker", "")

        # Limit context size — drop raw field lists that add noise
        context_for_prompt = {
            k: v for k, v in ctx.items()
            if k not in ("is_mock",)
        }

        return template.format(
            client_name=client_name,
            ticker=ticker,
            context_json=json.dumps(context_for_prompt, indent=2, default=str),
        )

    async def generate(self, command: str, ctx: dict) -> str:
        """
        Async: call Claude API for a command + context and return formatted text.

        Args:
            command: command name (e.g. "client-review")
            ctx:     context dict from ClientService

        Returns:
            Formatted response string (Telegram-ready markdown)
        """
        is_mock = ctx.get("is_mock", False)
        mock_banner = "⚠️ *MOCK MODE* — Data below is illustrative only.\n\n" if is_mock else ""

        system_prompt = self._build_system_prompt(command)
        user_prompt = self._build_user_prompt(command, ctx)

        logger.info("Calling Claude API | command=%s | model=%s", command, self.model)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            response_text = message.content[0].text
            logger.info(
                "Claude API response | tokens_in=%d tokens_out=%d",
                message.usage.input_tokens,
                message.usage.output_tokens,
            )
            return mock_banner + response_text

        except anthropic.AuthenticationError:
            logger.error("Claude API authentication failed — check ANTHROPIC_API_KEY")
            raise
        except anthropic.RateLimitError:
            logger.warning("Claude API rate limit hit")
            raise
        except Exception as e:
            logger.exception("Claude API error: %s", e)
            raise
