# Data Model: Chat UI Layout (Presentation Layer)

**Feature**: 002-chat-ui-layout | **Date**: 2026-06-21

This feature does not introduce new persisted entities. It reuses session state from feature 001.

## Session State (unchanged keys)

| Key | Type | Purpose |
|-----|------|---------|
| `messages` | `list[dict]` | Chat history (`role`, `content`, optional `report`) |
| `run_handle` | `RunHandle \| None` | Background run reference |
| `run_status` | `str` | `idle` \| `running` \| `completed` \| `failed` |
| `events` | `list[AgentEvent]` | Flat event list for trace tree |
| `report` | `FinalReport \| None` | Latest completed report |

## UI Zones (new conceptual layout)

| Zone | Location | Content |
|------|----------|---------|
| Banner | Main top | Medical disclaimer (compact) |
| Conversation | Main middle | `st.chat_message` history |
| Empty state | Main middle (pre-first-message) | Uniform example pills |
| Input | Main bottom (pinned) | `st.chat_input` with PDF accept |
| Activity | Sidebar | Live/completed agent trace |
| Session | Sidebar footer | "New case" reset button |

## Example Prompt (presentation mapping)

| Display label | Full submitted text |
|---------------|---------------------|
| Short clinical shorthand | Full sentence from `_EXAMPLES` in suggestions.py |

No schema change — label-to-text mapping is a UI-only constant.
