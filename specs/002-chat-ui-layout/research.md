# Research: Chat UI Layout Redesign

**Feature**: 002-chat-ui-layout | **Date**: 2026-06-21

## Decision 1: Main column vs. split columns

**Decision**: Remove the two-column main layout; dedicate the primary area to chat only.

**Rationale**: Streamlit `st.chat_input` is designed to pin to the bottom of the viewport when it is the last element in the main script flow. A 40% side column for agent activity competes with chat width and breaks the familiar single-column chat pattern.

**Alternatives considered**:
- Keep columns but narrow trace column → still splits attention; rejected.
- Tabs (Chat | Activity) → hides live trace during chat; rejected.

## Decision 2: Agent activity placement

**Decision**: Render `agent_trace` exclusively inside `st.sidebar`.

**Rationale**: Matches ChatGPT/Claude mental model — conversation in center, "thinking" in a secondary panel. Sidebar is collapsible on narrow viewports.

**Alternatives considered**:
- Inline `st.status` blocks in assistant chat message → duplicates sidebar; could add later as enhancement.
- Popover for trace → poor discoverability during long runs; rejected.

## Decision 3: Uniform example prompts

**Decision**: Use `st.pills` with short fixed labels; map each label to a full clinical example string stored in a tuple list.

**Rationale**: Pills render at consistent size regardless of label length. Truncated button text in equal columns still wraps to different heights.

**Alternatives considered**:
- CSS `min-height` on `st.button` → fragile across Streamlit versions; fallback only.
- `st.columns` + truncated labels → current broken behavior; rejected.

## Decision 4: Widget order in main column

**Decision**: Order = disclaimer → messages → suggestions (empty state) → `st.chat_input`. No widgets after chat input.

**Rationale**: Streamlit pins chat input to bottom only when nothing follows it in the main area. "New case" currently below input breaks the pattern.

## Decision 5: Live trace refresh

**Decision**: Preserve existing `@st.fragment(run_every="0.7s")` pattern; relocate fragment to sidebar block.

**Rationale**: Proven in feature 001; moving code block is sufficient — no new polling mechanism needed.
