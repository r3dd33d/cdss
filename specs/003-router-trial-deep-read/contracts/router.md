# Contract: Message Router

**Feature**: 003-router-trial-deep-read

## Interface

```python
async def route_message(
    text: str,
    *,
    has_prior_report: bool = False,
) -> RouteDecision:
    ...
```

## Modes

| Mode | Behavior |
|------|----------|
| `chat` | Return `ChatAgent` reply; no `Runner.run()` |
| `research` | Proceed to `_submit_message()` / pipeline |
| `clarify` | Return assistant message with `clarifying_question`; no run |

## Overrides (UI)

- Example pill clicks → force `research` (skip router LLM)
- PDF upload with empty text → force `research`
- Empty text → validation error (unchanged)

## Router prompt constraints

- Output JSON only
- `clarify` only when genuinely ambiguous
- Patient case with condition/stage/biomarker → `research`
- General oncology education → `chat`

## Tests

- `"What is HER2?"` → `chat`
- `"Stage II HER2+ breast cancer, no treatment"` → `research`
- `"help"` → `clarify`
- Pill selection → `research` (UI override, not router)
