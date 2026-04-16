# API Conventions — Aureus RM Copilot

## MCP Tool Conventions

All data access goes through MCP tool calls declared in `.mcp.json`. No direct API calls, no hardcoded data.

### Tool Naming

| Category | Prefix | Examples |
|----------|--------|---------|
| CRM | `crm.` | `crm.get_client_profile`, `crm.get_recent_interactions` |
| Portfolio | `portfolio.` | `portfolio.get_holdings`, `portfolio.get_exposure_breakdown` |
| Suitability | `suitability.` | `suitability.get_risk_profile`, `suitability.validate_recommendation_framing` |
| Market | `market.` | `market.get_company_snapshot`, `market.get_price_history` |
| Fundamentals | `fundamentals.` | `fundamentals.get_financials`, `fundamentals.get_estimates` |
| Research | `research.` | `research.get_earnings_summary`, `research.search_news` |
| House View | `house_view.` | `house_view.get_internal_view` |
| Compliance | `compliance.` | `compliance.check_disclosures`, `compliance.get_approved_products` |
| Notes | `notes.` | `notes.save_meeting_prep`, `notes.save_action_item` |

### Tool Call Rules

- Execute all required tool calls before assembling any response
- Never call tools in the wrong order — CRM/suitability data must be retrieved before portfolio fit assessment
- If a tool returns empty or stub data: note the gap, continue with available data, do not infer
- Tool results are session-scoped — do not reference results from a prior session

### Adding a New Tool

1. Add the server entry to `.mcp.json` with transport config and tool schema
2. Document the connector interface in `docs/connector-requirements.md`
3. Add expected output schema to `schemas/` if the tool produces structured output
4. Update the relevant command `.md` files to include the new tool call in their retrieval steps

### Placeholder vs Live Connectors

Placeholder connectors (`"placeholder": true` in `.mcp.json`) return empty/stub responses and do not error. Swap a placeholder for a live connector by:
1. Replace `"command": "placeholder"` with the actual server binary/script
2. Add authentication env vars to the `"env"` block
3. Remove `"placeholder": true`
4. Verify output matches the schema in `schemas/`

## Telegram Bot Conventions

- All message routing goes through `services/command_router.py`
- Bot handlers in `bot/` are thin wiring only — they call services, never implement logic
- Message length: split at `_split_message()` in the bot module — do not bypass this
- Never log client data to Telegram or stdout in production — use `hooks/crm_logger.py`

## Output Schemas

- All structured outputs have a JSON Schema in `schemas/`
- Schema filenames match the command name: `portfolio_fit.json` for `/portfolio-fit`
- Validate output against schema before delivering to RM when in strict mode
