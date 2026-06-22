# Feature Specification: Inline Chain-of-Thought Agent Trace

**Feature Branch**: `004-chat-thinking-trace`  
**Created**: 2026-06-22  
**Status**: Draft  
**Input**: User description: "Replace the sidebar 'Agent activity' panel with an inline, in-chat chain-of-thought view of the multi-agent pipeline's progress."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the assistant's work unfold inside the chat (Priority: P1)

A clinician submits a case. Instead of a small collapsing chip in the sidebar, a "thinking" block appears directly in the chat thread, as part of the assistant's turn, and fills in step by step in plain language as the pipeline works — e.g. "Analyzing your question", "Searching guideline sources", "Reading sources", "Checking clinical trials", "Exploring off-label options", "Summarizing findings". When the work finishes, the final report appears below the thinking block in the same turn.

**Why this priority**: This is the core of the request. Today the activity is in the sidebar, collapses on click, and shows raw labels like "run_started" — it fails to communicate what the system is doing. Putting a readable progress narrative in the chat is the entire value of the feature and is independently shippable.

**Independent Test**: Submit a research case and confirm a progress narrative appears in the chat thread (not the sidebar), advances through readable steps as the run proceeds, and is followed by the final report in the same assistant turn.

**Acceptance Scenarios**:

1. **Given** a clinician has submitted a diagnosis, **When** the pipeline starts, **Then** a thinking block appears in the chat thread showing the current step in plain language.
2. **Given** the pipeline is moving through phases, **When** each phase begins or completes, **Then** a corresponding readable step line appears or updates in the thinking block within ~1 second.
3. **Given** the pipeline finishes successfully, **When** the final report is ready, **Then** the report is shown in the same assistant turn directly below the completed thinking block.
4. **Given** raw event names exist internally (e.g. `run_started`, `AGENT_SPAWNED`), **When** they are shown to the user, **Then** the user only sees friendly phrasing, never raw enum identifiers.

---

### User Story 2 - Understand fan-out: how many agents are reading what (Priority: P2)

When the system spawns multiple reader agents to read multiple articles or trials in parallel, the thinking block tells the user how many — e.g. "Spawning 5 agents to read 5 sources", "Reading 5 sources", "Reviewing 3 clinical trials".

**Why this priority**: The user specifically wants to see the parallel fan-out ("how many agents it spawns to read the articles"). It depends on US1 being in place but adds the richness that makes the trace feel like a real chain of thought.

**Independent Test**: Submit a case that discovers multiple sources/trials and confirm the thinking block reports the count of spawned readers and items processed, matching the actual run.

**Acceptance Scenarios**:

1. **Given** the coordinator spawns N reader agents, **When** the spawn happens, **Then** the thinking block shows a line that includes the count N.
2. **Given** sources or trials are discovered, **When** counts are available in the activity stream, **Then** the relevant step surfaces those counts (e.g. number of sources searched, trials reviewed).
3. **Given** counts are not available for a step, **When** that step renders, **Then** it shows a sensible generic phrase without an empty or "None" count.

---

### User Story 3 - Review or hide the reasoning after completion (Priority: P3)

After a run completes, the thinking block remains in the thread above its report. The user can expand it to review every step, or collapse it to focus on the report. Expanding and collapsing works reliably and does not snap shut on its own.

**Why this priority**: The current sidebar version auto-collapses and can't be reopened, which is the user's stated frustration. Reliable expand/collapse is important but secondary to getting the narrative into the chat at all.

**Independent Test**: After a completed run, collapse and expand the thinking block several times and confirm it honors each action and preserves the full step history; reload/redisplay of prior turns keeps each turn's thinking block intact.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the user collapses the thinking block, **Then** it stays collapsed until the user expands it again.
2. **Given** a completed run, **When** the user expands the thinking block, **Then** all steps from that run are visible in order.
3. **Given** multiple cases have been run in one session, **When** the user scrolls the thread, **Then** each assistant turn shows its own thinking block tied to that turn's report.

---

### Edge Cases

- **Run fails mid-pipeline**: the thinking block must show the step that was in progress as failed and surface a readable error, instead of silently disappearing.
- **Conversational (non-research) replies**: a quick chat/clarify reply that does not run the pipeline should not show a thinking block (nothing to narrate).
- **Very fast steps**: steps that complete almost instantly should still register so the history is complete, even if the user does not visually catch them streaming.
- **Unknown/new event or agent types**: an activity item that has no friendly mapping yet must degrade to a safe generic phrase, never a raw identifier or a crash.
- **No activity received**: if a run produces no intermediate activity before completing, the block should show at least a start and a completion step.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display pipeline progress as a "thinking" block inside the chat thread, within the assistant's turn, rather than in the sidebar.
- **FR-002**: The thinking block MUST update in near-real-time as the pipeline produces activity, advancing through steps while the run is in progress.
- **FR-003**: Each step MUST be shown in human-readable, sentence-case language; raw internal identifiers (event or agent type codes) MUST NOT be shown to the user.
- **FR-004**: The system MUST translate the activity the pipeline actually emits — run start/complete/fail and the per-agent spawn lifecycle (spawned, started, completed, failed, each tagged with its agent type and duration) — into friendly step phrasing in a single presentation/labeling layer. Fan-out counts are derived by counting spawned leaf agents of a given type (e.g. one source = one reader); the labeling layer MUST NOT depend on activity types the core does not emit (e.g. source-discovered, model-call, phase-completed are reserved but currently unused).
- **FR-005**: When the activity stream reports counts (e.g. number of reader agents spawned, number of sources or trials), the corresponding step MUST surface those counts in its phrasing.
- **FR-006**: On successful completion, the final report MUST appear in the same assistant turn, positioned below the completed thinking block.
- **FR-007**: On failure, the thinking block MUST mark the in-progress step as failed and present a readable error message in the thread.
- **FR-008**: After a run completes, the thinking block MUST remain in the thread and be expandable and collapsible by the user, honoring each action and preserving the full ordered step history.
- **FR-009**: Each assistant turn MUST retain its own thinking block, so prior cases in the same session keep their reasoning history alongside their reports. Consecutive runs in one session MUST be isolated — a new run's live activity buffer is cleared when that run starts, so steps never bleed from a previous turn into a new one.
- **FR-010**: A conversational reply that does not invoke the research pipeline MUST NOT render a thinking block.
- **FR-011**: Unmapped or unknown activity items MUST degrade gracefully to a generic readable phrase without error.
- **FR-012**: The clinical core MUST remain free of presentation/UI concerns (no UI dependency added to the headless pipeline); the friendly phrasing lives only in the presentation layer.

### Key Entities *(include if feature involves data)*

- **Activity step (presentation)**: a single user-facing line in the thinking block — derived from one or more underlying pipeline activity events — with a readable label, an optional count, and a state (in progress, done, failed).
- **Thinking block (presentation)**: the ordered collection of activity steps for one assistant turn, with an overall state (running, completed, failed) and an expanded/collapsed display state.
- **Pipeline activity event (existing)**: the underlying signal already emitted by the core (type, originating agent, optional counts/payload, timing); consumed read-only by the presentation layer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of research runs, progress is shown inside the chat thread and never requires opening the sidebar to understand what the system is doing.
- **SC-002**: 0 raw internal identifiers (e.g. "run_started", "AGENT_SPAWNED") are visible to the user across all steps.
- **SC-003**: A new step becomes visible within ~1 second of the underlying activity occurring during a live run.
- **SC-004**: When parallel readers are used, the displayed count of spawned readers and items processed matches the actual run in 100% of cases where counts are available.
- **SC-005**: After completion, expand/collapse of the thinking block succeeds on every attempt and never auto-collapses without user action.
- **SC-006**: A new user can correctly describe, in their own words, what the assistant did during a run (e.g. "it read 5 articles then summarized") after watching the trace once — validated informally with at least 3 people.

## Assumptions

- The existing activity stream carries enough information (event type, agent type, timing, per-agent spawn lifecycle) to produce the desired steps and counts; research confirmed **no event-schema change is required** — counts come from counting spawned leaf agents.
- A small, fixed set of pipeline phases (intake/analysis, source search & reading, clinical trials, off-label hypotheses, synthesis) is sufficient to structure the narrative; deep per-event detail can be summarized into these phases.
- The thinking block is grouped by phase rather than showing every low-level event verbatim, to keep it readable.
- Sentence-case, plain-language phrasing (matching the app's existing tone) is the desired style; no localization is required for this iteration.
- Scope is the Streamlit UI layer (`app/`) only; the clinical pipeline behavior and outputs are unchanged.
- The sidebar "Agent activity" panel is replaced by this inline view; retaining a sidebar mirror is out of scope for this iteration.
