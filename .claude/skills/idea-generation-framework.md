# Idea Generation Framework — Skill Reference

## Purpose
Guide Aureus responses for `/idea_generation`. Ensures ideas are mandate-aware, not generic stock picks.

## How Idea Generation Works

1. **Start with the mandate.** The client's risk profile, investment objective, and any sector restrictions define the filter. A High conviction idea that violates the mandate is not an idea — it is a risk.
2. **Screen by conviction.** High conviction ideas surface first. Medium conviction ideas are included if they fit the mandate. Low conviction ideas are not surfaced unless the universe is otherwise empty.
3. **One rationale per idea.** Each idea needs one sentence explaining why it fits this specific client — not a generic description of the stock.

## Idea Output Rules
- Max 3 ideas per output
- Each idea: ticker, sector, conviction level, one-line rationale specific to this client
- Always note: "Validate against suitability before raising. Use /thesis_check [ticker] for detail."
- RM framing: how to open the idea conversation (not "I recommend" — "I've been looking at...")

## What Not To Do
- Do not surface ideas that violate the client's mandate
- Do not present ideas as recommendations
- Do not list more than 3 ideas — quality over quantity
