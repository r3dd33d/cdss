# Contract: UI Layout Zones

**Feature**: 002-chat-ui-layout | **Date**: 2026-06-21

Defines widget order and responsibilities. Does not change the runner bridge contract from feature 001.

## Main column (top → bottom)

1. **Disclaimer** — `disclaimer.render()`; compact warning banner.
2. **Messages** — iterate `st.session_state.messages`; assistant reports via `report_view.render()`.
3. **Suggestions** — `suggestions.render()` only when `messages` empty and `run_status == idle`.
4. **Chat input** — `st.chat_input(...)` MUST be the final Streamlit widget in this column.

**Invariant**: No buttons, captions, or inputs may appear after step 4 in the main column.

## Sidebar (top → bottom)

1. **Heading** — "Agent activity" (sentence case).
2. **Live trace** — when `run_status == running`: `@st.fragment` drains events and calls `agent_trace.render()`.
3. **Static trace** — when events exist and not running: `agent_trace.render(events)`.
4. **Empty state** — caption when no events.
5. **New case** — calls `reset()` + `st.rerun()`.

## Suggestions component

- Input: none (reads constants).
- Output: full example string on selection, or `None`.
- Constraint: all pill/card controls equal visual size.

## Agent trace component

- Input: `list[AgentEvent]`.
- Output: rendered status tree (unchanged event mapping).
- Constraint: must render read-only; no pipeline calls.

## Runner bridge (unchanged)

- `start_run(runner, text, files)` — invoked from chat input handler only.
- Event drain via `handle.drain_events()` inside sidebar fragment.
