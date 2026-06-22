# Phase 1 Data Model: Inline Chain-of-Thought Agent Trace

Presentation-layer entities only (in `app/`). No core/Pydantic-core changes. These can be plain dataclasses/dicts held in session state.

## TraceStep

A single user-facing line in the thinking block, derived from one phase of the run.

| Field | Type | Notes |
|-------|------|-------|
| `phase` | str | Stable phase key (e.g. `analyze`, `read_sources`, `trials`, `summarize`). Used to dedupe/merge events of the same phase. |
| `label` | str | Friendly, sentence-case text shown to the user (e.g. "Reading 5 sources"). Never a raw enum. |
| `count` | int \| None | Optional fan-out count surfaced in the label (e.g. spawned readers). `None` when not applicable. |
| `state` | str | One of `running`, `done`, `failed`. |

**Validation / rules**:
- A phase appears **at most once** per run; repeated events of the same phase update the existing step (count grows, state advances `running → done`/`failed`).
- `label` MUST be derived from `event_type`/`agent_type`/`count` only — never from patient text (Principle V).
- Unknown `agent_type` → a single generic step (`phase="other"`, label "Working…").

## ThinkingTrace (per assistant turn)

The ordered set of `TraceStep`s for one run, plus overall state.

| Field | Type | Notes |
|-------|------|-------|
| `steps` | list[TraceStep] | Ordered by first occurrence (intake → … → synthesize). |
| `state` | str | `running` while live; `completed` or `failed` at end. |

**State transitions**:
- `RUN_STARTED` → trace `running`, seed a "Starting…" / analyze step.
- `AGENT_SPAWNED`/`AGENT_STARTED` (agent_type X) → ensure step for X's phase exists, `state=running`; if leaf type (SOURCE_READER/TRIAL_READER), increment `count`.
- `AGENT_COMPLETED` (agent_type X) → that phase step `state=done`.
- `AGENT_FAILED` → that phase step `state=failed`.
- `RUN_COMPLETED` → trace `completed`; any lingering `running` steps marked `done`.
- `RUN_FAILED` → trace `failed`; in-progress step marked `failed`, append a readable error line (FR-007). Error text is read from the failing event's payload (`AGENT_FAILED.payload["error"]` or `RUN_FAILED.payload["error"]`) — never from patient input.

## Storage / lifecycle

- **Run start (isolation — F2)**: the live buffer (`st.session_state.events`) MUST be cleared in `_start_research_run()` when a run begins, not only on `reset()`. This prevents a follow-up research run in the same session from inheriting the previous turn's steps (FR-009).
- **Live**: events accumulate in the transient session buffer (`st.session_state.events`); `derive_steps(buffer)` is recomputed each fragment tick (pure function → cheap, idempotent).
- **On completion**: the derived `steps` (+ run state) are attached to the appended assistant message:
  `{"role": "assistant", "content": "", "report": FinalReport, "steps": [...], "trace_state": "completed"}`.
- **History render**: the chat loop reads `msg["steps"]` and renders a static block above `msg["report"]` (FR-009).
- **Reset / new case**: `reset()` clears the live buffer; per-message steps vanish with the cleared `messages` list. No global trace state persists.

## Message shape change (session.py)

Assistant report messages gain two optional keys (`steps`, `trace_state`). The existing `report`, `content`, `role` keys are unchanged. Conversational replies (no pipeline) carry **no** `steps` key → no block rendered (FR-010).
