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

Implemented in `cdss/agents/router/router_agent.py`. **Not** spawned via `AgentFactory` (pre-pipeline; see FR-007).

```python
async def chat_reply(
    text: str,
    *,
    prior_report: FinalReport | None = None,
) -> str:
    ...
```

Implemented in `cdss/agents/chat/chat_agent.py`. **Not** spawned via `AgentFactory`.

## Sync bridge (Streamlit)

`app/chat_bridge.py` exposes synchronous helpers for the UI thread:

```python
def route_and_reply(text: str, *, has_prior_report: bool = False, prior_report=None) -> tuple[RouteDecision, str | None]:
    """asyncio.run(route_message); if mode==chat, also returns chat_reply text."""
```

`app/main.py` MUST NOT call `asyncio` directly — use `chat_bridge` only.

## Modes

| Mode | Behavior |
|------|----------|
| `chat` | Call `chat_reply()`; no `Runner.run()` |
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

## Trace events (optional)

UI MAY publish lightweight events before `RUN_STARTED`:
- `route_decided` with `mode`
- `chat_replied` when chat path taken

Pipeline agents (intake onward) MUST use factory spawn per FR-007.

## Tests

- `"What is HER2?"` → `chat`
- `"Stage II HER2+ breast cancer, no treatment"` → `research`
- `"help"` → `clarify`
- Pill selection → `research` (UI override, not router)
- SC-001: chat path wall clock &lt; 5 s with mocked LLM (T024)
