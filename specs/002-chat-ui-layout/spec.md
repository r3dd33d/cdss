# Feature Specification: Chat UI Layout Redesign

**Feature Branch**: `002-chat-ui-layout`  
**Created**: 2026-06-21  
**Status**: Draft  
**Input**: Redesign the clinical research chat interface to follow familiar AI-chat patterns: message input fixed at the bottom of the page, conversation and in-progress work displayed above it, agent activity moved to a sidebar panel, and uniformly sized example prompts on the empty state.

## Overview

The current interface splits the screen into two equal-weight columns (chat and agent activity), which makes the chat feel cramped and the example prompts visually uneven. Users expect a single primary conversation column with the input anchored at the bottom — the same pattern used by mainstream AI chat products — while background agent work appears in a secondary sidebar rather than competing for horizontal space.

This feature is a **presentation-only** change. It does not alter the multi-agent pipeline, report content, event model, or runner interface established in feature 001.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chat with input anchored at the bottom (Priority: P1) 🎯 MVP

A user opens the app and sees a single main conversation area. Their messages and the assistant's report appear above a message box that stays at the bottom of the viewport. As the conversation grows, earlier messages scroll upward while the input remains accessible without hunting for it below other controls.

**Why this priority**: This is the core usability fix — without it, the app does not feel like a chat product and daily use is awkward.

**Independent Test**: Open the app on desktop, submit a message, receive a report, and verify the input remains at the bottom throughout; no secondary controls appear below the input in the main area.

**Acceptance Scenarios**:

1. **Given** an empty session, **When** the user views the main area, **Then** the message input is visible at the bottom and no other interactive controls sit below it in the main column.
2. **Given** a session with multiple user and assistant messages, **When** the user scrolls, **Then** messages appear above the input and the input stays pinned at the bottom of the page.
3. **Given** a running pipeline, **When** the user views the main area, **Then** the conversation (user message and any assistant placeholder) remains above the input without the layout jumping.

---

### User Story 2 - Agent activity in a sidebar (Priority: P1)

While a research run executes, the user sees a live tree of spawning and completing agents in a sidebar panel — not in a second main column. When idle, the sidebar shows a lightweight empty state. When a run completes, the trace remains visible in the sidebar for reference.

**Why this priority**: Separating "thinking" from "conversation" matches user mental models from other AI assistants and frees the main area for chat content.

**Independent Test**: Start a run and confirm agent spawn/completion events appear only in the sidebar; the main column width is dedicated to chat.

**Acceptance Scenarios**:

1. **Given** a new session, **When** no run is active, **Then** the sidebar shows a brief placeholder indicating agent activity will appear during a run.
2. **Given** a running pipeline, **When** agents spawn and complete, **Then** the live trace updates in the sidebar with status and duration, without duplicating the trace in the main column.
3. **Given** a completed run, **When** the user reviews the session, **Then** the final agent trace remains visible in the sidebar.

---

### User Story 3 - Uniform example prompts on empty state (Priority: P2)

Before the first message, the user sees a row of example prompts that are visually equal in size regardless of text length. Clicking one submits the full clinical example (not a truncated label) as the user's first message.

**Why this priority**: Uneven chips look broken and undermine trust; equal sizing is a polish requirement that improves first impressions.

**Independent Test**: Load the empty state and measure that all example controls share the same height and width within their row; click each and verify the full example text is sent.

**Acceptance Scenarios**:

1. **Given** an empty session, **When** the user views the example prompts, **Then** all prompts in the row have identical dimensions (height and width within their slot).
2. **Given** an example prompt with a short label, **When** the user clicks it, **Then** the complete underlying example text is submitted as the user message.
3. **Given** the user has already sent a message, **When** they view the chat, **Then** the example prompts are hidden.

---

### User Story 4 - Session controls in the sidebar (Priority: P3)

The user can start a new case from the sidebar without scrolling past the chat input. The medical disclaimer remains visible but does not dominate the conversation area.

**Why this priority**: Keeps the main column focused on chat; session-level actions belong with other meta information in the sidebar.

**Independent Test**: Complete a run, click "New case" in the sidebar, and verify messages, trace, and run state reset.

**Acceptance Scenarios**:

1. **Given** a session with messages and a completed run, **When** the user clicks "New case" in the sidebar, **Then** the conversation, agent trace, and run state reset to idle.
2. **Given** any session state, **When** the user views the app, **Then** the medical disclaimer is visible without occupying more vertical space than necessary.

---

### Edge Cases

- **Very long report**: tabbed report content scrolls within the assistant message bubble; input remains at bottom.
- **Sidebar collapsed** (narrow viewport): agent trace remains accessible when the user expands the sidebar; chat input still anchors at bottom in the main area.
- **Run fails mid-session**: error message appears as an assistant message in the main area; failed agent nodes appear in the sidebar trace.
- **Rapid rerun / fragment refresh**: sidebar trace and main chat stay in sync without duplicate messages or lost events.
- **Example click during idle**: selecting an example immediately starts the same flow as typing and submitting manually.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main conversation area MUST occupy the full primary content width (no second main column for agent activity).
- **FR-002**: The message input MUST be the last interactive element in the main column so it remains anchored at the bottom of the page.
- **FR-003**: User messages, assistant reports, and error messages MUST render above the message input in chronological order.
- **FR-004**: Agent activity (live trace tree with status and duration) MUST render exclusively in a sidebar panel, not in the main conversation column.
- **FR-005**: The sidebar MUST show a concise empty-state message when no run events exist.
- **FR-006**: During an active run, the sidebar trace MUST update in real time until the run reaches a terminal state.
- **FR-007**: Example prompts on the empty state MUST present controls of uniform size regardless of label length.
- **FR-008**: Selecting an example prompt MUST submit the full predefined example text, not a truncated display label.
- **FR-009**: Example prompts MUST be hidden once the user has sent at least one message.
- **FR-010**: A "New case" control MUST be available in the sidebar and MUST reset conversation, trace, and run state.
- **FR-011**: The medical disclaimer MUST remain visible on every page view; compact presentation is acceptable.
- **FR-012**: This feature MUST NOT change the runner interface, agent pipeline, event types, or report structure from feature 001.
- **FR-013**: The UI layer MUST continue to contain no agent, LLM, or external-call logic (constitutional separation preserved).

### Key Entities

- **Conversation message**: user or assistant turn displayed in the main column (text content or structured report reference).
- **Agent trace event**: existing typed lifecycle event consumed by the sidebar to build the spawn tree (unchanged from feature 001).
- **Example prompt**: a display label paired with a full clinical example string; clicking submits the full string.
- **Session state**: messages list, run status, event list, and run handle — reset together on "New case".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a manual review of the empty state on a standard desktop viewport (≥1280px wide), all example prompt controls measure within 4px of each other in height and width.
- **SC-002**: 100% of acceptance scenarios for User Stories 1 and 2 pass in a single end-to-end walkthrough (submit message → watch sidebar trace → receive report).
- **SC-003**: No interactive control other than the message input appears below the input in the main column during idle, running, or completed states.
- **SC-004**: Users can start a new case from the sidebar in one click without scrolling past the message input.
- **SC-005**: All existing automated tests for the headless core and runner continue to pass unchanged; no new pipeline behavior is introduced.
- **SC-006**: The import-direction guard confirming UI/core separation continues to pass after the layout change.

## Assumptions

- The application remains a single-page Streamlit chat experience (no multipage navigation).
- Desktop-first layout is sufficient for v1; mobile sidebar behavior follows Streamlit's default collapsible sidebar.
- Example prompt labels may be shortened for display as long as the full clinical text is submitted on selection.
- Agent trace rendering reuses the existing event list and status mapping from feature 001; only placement and styling change.
- No new persistence, authentication, or theming system is required beyond optional minor visual polish consistent with the existing app.

## Dependencies

- Feature 001 (`001-cdss-multi-agent-pipeline`) merged to `main`: runner bridge, session state, agent trace component, and report view must remain functional.
- Streamlit chat primitives (`chat_message`, `chat_input`) and sidebar layout are the intended presentation mechanism.
