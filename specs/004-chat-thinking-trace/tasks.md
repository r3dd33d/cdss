# Tasks: Inline Chain-of-Thought Agent Trace

**Feature**: 004-chat-thinking-trace | **Branch**: `004-chat-thinking-trace`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Contracts**: [contracts/trace-ui.md](contracts/trace-ui.md)

Scope is UI-only (`app/`). The headless core (`cdss/`) is not touched. Labeling logic stays Streamlit-free so it is unit-testable.

---

## Phase 1: Setup

- [x] T001 Confirm UI test dir exists at `tests/app/unit/` (create `tests/app/unit/__init__.py` if missing) so new UI tests are collectable.

---

## Phase 2: Foundational (blocking prerequisites for all stories)

The step model + labeling function are the backbone every story renders from.

- [x] T002 Create `TraceStep` and `ThinkingTrace` presentation types (plain dataclasses: `phase`, `label`, `count`, `state`; and `steps`, `state`) in `app/components/trace_labels.py`, importing **no** Streamlit (per contracts/trace-ui.md §1, data-model.md).
- [x] T003 Implement `derive_steps(events: list[AgentEvent]) -> list[TraceStep]` in `app/components/trace_labels.py`: map `AgentType`→phase and friendly label per the research.md phase table, drive `state` from RUN_STARTED / AGENT_SPAWNED / AGENT_STARTED / AGENT_COMPLETED / AGENT_FAILED / RUN_COMPLETED / RUN_FAILED, merge repeated phases (one step per phase), and degrade unknown agent types to a generic "Working…" step. Pure + idempotent; never reads patient text (FR-003, FR-004, FR-011).
- [x] T004 [P] Unit-test `derive_steps` in `tests/app/unit/test_trace_labels.py` with synthetic event lists: ordered phases, unknown-type fallback, no raw enum strings in any label, idempotent re-derivation as the buffer grows (SC-002).

**Checkpoint**: `derive_steps` produces ordered, readable steps from a run's events with no Streamlit dependency.

---

## Phase 3: User Story 1 — See the assistant's work inside the chat (Priority: P1) 🎯 MVP

**Goal**: Live, readable thinking block streams inside the assistant chat turn (not the sidebar); report renders below it on completion.
**Independent test**: Submit a case → progress narrative appears in the chat thread and advances through readable steps, followed by the report in the same turn.

- [x] T005 [US1] Implement `render_live(steps)` in `app/components/thinking_trace.py`: one `st.status(current_step_label, state="running")` with prior steps listed as done/failed lines; readable labels only (contracts/trace-ui.md §2).
- [x] T006 [US1] In `app/main.py`, render the live block **inside the chat thread**: while `run_status == "running"`, open `st.chat_message("assistant")` and run the `@st.fragment(run_every="0.7s")` there — drain events into `st.session_state.events`, call `derive_steps`, then `render_live` (moves the loop out of the sidebar; FR-001, FR-002).
- [x] T007 [US1] In `app/main.py` `_start_research_run()`, clear `st.session_state.events` when a run starts, so consecutive runs don't inherit prior steps (F2, FR-009 isolation).
- [x] T008 [US1] On `handle.done()`, append the assistant message carrying `report`, the derived `steps`, and `trace_state="completed"`, then `st.rerun()`; ensure the report renders below the completed block in the same turn (FR-006).
- [x] T009 [US1] **Remove** `_render_sidebar_trace` and the sidebar `st.subheader(":material/psychology: Agent activity")` block from `app/main.py`; keep the "New case" button. (Relocation — Removal Plan §1.)
- [x] T010 [US1] **Delete** `app/components/agent_trace.py` and remove `agent_trace` from the `from app.components import …` line in `app/main.py` (Removal Plan §2).

**Checkpoint**: MVP — inline streaming trace works end-to-end; sidebar trace gone; report appears under the block.

---

## Phase 4: User Story 2 — Show fan-out counts (Priority: P2)

**Goal**: Surface how many agents/articles/trials, e.g. "Reading 5 sources", "Reviewing 3 clinical trials".
**Independent test**: Run a case with multiple sources/trials → displayed counts match the run.

- [x] T011 [US2] Extend `derive_steps` in `app/components/trace_labels.py` to count `AGENT_SPAWNED` events per leaf `AgentType` (SOURCE_READER, TRIAL_READER) and fold the count into the phase label ("Reading {N} sources", "Reviewing {N} trials"); omit count gracefully when zero/absent (FR-005, research R3).
- [x] T012 [P] [US2] Extend `tests/app/unit/test_trace_labels.py`: multiple SOURCE_READER/TRIAL_READER spawns yield correct counts in labels; no count shown when none (SC-004).

**Checkpoint**: Counts appear and match the run.

---

## Phase 5: User Story 3 — Review/hide reasoning after completion (Priority: P3)

**Goal**: Completed block persists above its report and reliably expands/collapses; failures are shown readably.
**Independent test**: After completion, collapse/expand repeatedly (persists); each prior turn keeps its own block; a failed run shows the failed step + error.

- [x] T013 [US3] Implement `render_static(steps, state)` in `app/components/thinking_trace.py`: `st.status(summary, state=<complete|error>, expanded=False)` listing all steps; summary "Thought through {N} steps" / "Stopped during {step}" (contracts/trace-ui.md §2).
- [x] T014 [US3] In `app/main.py` history loop, for assistant messages that have `steps`, call `render_static(msg["steps"], msg["trace_state"])` **above** `report_view.render(msg["report"])` — rendered outside any `run_every` fragment so expand/collapse persists across reruns (FR-008, SC-005 — fixes the auto-collapse bug).
- [x] T015 [US3] Handle the failure path: on `handle.error()` / `RUN_FAILED`, mark the in-progress step failed and surface the error line from the failing event's `payload["error"]`; append the assistant message with `trace_state="failed"` (FR-007, F3).
- [x] T016 [US3] Verify conversational (chat/clarify) replies append a message with **no** `steps` key so no block renders for non-research turns (FR-010).

**Checkpoint**: Persistent, per-turn, expandable history with graceful failure rendering.

---

## Phase 6: Polish & Cross-Cutting

- [x] T017 Audit `app/state/session.py`: demote `events` to a transient live buffer cleared on run start and `reset()`; remove the `report` key if unread (`report_view` reads `msg["report"]`, not `session_state.report`) — no orphaned state (Removal Plan §3).
- [x] T018 Removal gate: run `grep -rn "agent_trace\|_render_sidebar_trace\|session_state.report" app/` and confirm no orphaned references remain (Removal Plan §4).
- [x] T019 [P] Run `make guards` (file-size <200/<400, `cdss/`-no-Streamlit import direction, comment length) and confirm `app/components/trace_labels.py` imports no Streamlit (Principle I, II, VII).
- [x] T020 Run full suite `.venv/bin/python -m pytest -q` (stays green) and walk the 9 manual checks in [quickstart.md](quickstart.md).

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T004)** must finish before any story.
- **US1 (T005–T010)** is the MVP and unblocks US2/US3 (they render from the same steps/components).
- **US2 (T011–T012)** depends only on `derive_steps` (T003) — can start once Foundational is done, but verify after US1 for the visible end-to-end.
- **US3 (T013–T016)** depends on US1's message shape (T008).
- **Polish (T017–T020)** last.

## Parallel Opportunities

- T004 (label tests) ∥ T005 (render_live) — different files.
- T012 (count tests) ∥ T013 (render_static) — different files.
- T019 (guards) ∥ T020 prep — independent checks.

## Implementation Strategy

- **MVP = Phases 1–3 (through T010):** inline streaming trace replaces the sidebar — already delivers the user's core ask.
- Add **US2** (counts) and **US3** (persistence/expand-collapse + failures) incrementally; each is independently demoable.
- Removal/clean-up tasks (T009, T010, T017, T018) ensure nothing orphaned per the user's explicit requirement.
