# Context: Inline Chain-of-Thought Agent Trace

**Feature**: 004-chat-thinking-trace  
**Depends on**: 001-cdss-multi-agent-pipeline, 002-chat-ui-layout, 003-router-trial-deep-read

## Mission

Move the multi-agent pipeline's progress out of the collapsing sidebar chip and into the chat thread as a live, readable chain-of-thought ("Analyzing… → Reading 5 sources → Summarizing"), so a clinician can watch what the assistant is doing without leaving the conversation.

## Current gaps

1. Activity renders in the **sidebar** (`app/main.py:_render_sidebar_trace`) via `agent_trace.render()` using `st.status(expanded=False)` — it auto-collapses and cannot be re-expanded.
2. Step labels are **raw enum values** (`run_started`, `AGENT_SPAWNED`) — `agent_trace.py` falls back to `e.event_type` / `e.agent_type` with no friendly mapping.
3. The trace is **detached from the assistant turn** — it lives in `st.session_state.events` (a single flat list), not attached to the report message, so it is not part of the chat history.
4. No fan-out narration: spawned-reader counts and source/trial counts in event payloads are never surfaced.

## This feature is UI-only (`app/`)

The headless core (`cdss/`) already emits all needed events (Principle IV). **No core changes** unless a count is genuinely missing from a payload. Friendly phrasing lives only in the presentation layer.

## Code paths

| Area | Path | Action |
|------|------|--------|
| Sidebar trace section | `app/main.py` (`_render_sidebar_trace`, sidebar `st.subheader("Agent activity")`) | **REMOVE** — relocated into chat |
| Old renderer | `app/components/agent_trace.py` | **REPLACE** with new in-chat thinking-block component |
| Event labeling | new `app/components/trace_labels.py` | friendly phrasing for EventType/AgentType + counts |
| In-chat block | new `app/components/thinking_trace.py` (or fold into chat render) | renders steps as `st.status`/`st.expander` inside `st.chat_message` |
| Live loop + message assembly | `app/main.py` (`_render_sidebar_trace` fragment, message append on completion) | move live fragment into the assistant turn; attach steps to the report message |
| Session shape | `app/state/session.py` (`events`, `report`, `messages`) | attach per-turn `steps` to assistant message; retire the global `events` list if orphaned |

## Event sources to map (read-only, already emitted)

`RUN_STARTED, AGENT_SPAWNED, AGENT_STARTED, SOURCE_DISCOVERED, SOURCE_FETCHED, LLM_CALL, AGENT_COMPLETED, AGENT_FAILED, PHASE_COMPLETED, RUN_COMPLETED, RUN_FAILED` × `AgentType` (INTAKE, RESEARCH_COORDINATOR, SOURCE_READER, TRIALS_COORDINATOR, TRIAL_READER, CROSS_INDICATION_COORD, REPORT_SYNTHESIZER, …).

## Out of scope

- Changing the agent pipeline, event schema, or core behavior (unless a count is missing).
- Keeping a sidebar mirror of activity (the sidebar panel is removed).
- Persisting traces across sessions; localization; token-level streaming of LLM output.
