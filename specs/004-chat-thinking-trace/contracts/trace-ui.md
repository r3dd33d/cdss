# Contract: Trace UI & Labeling

Defines the interfaces the feature exposes within `app/`. Two narrow surfaces: a Streamlit-free labeling function and a render component.

## 1. Labeling (`app/components/trace_labels.py`) — Streamlit-free, unit-tested

```python
def derive_steps(events: list[AgentEvent]) -> list[TraceStep]:
    """Group a run's events into ordered, friendly steps with counts and state.
    Pure: no Streamlit, no I/O. Deterministic for a given event list."""
```

**Contract**:
- Input: the run's events in arrival order (the live buffer or a message's captured events).
- Output: `list[TraceStep]` ordered by first occurrence; one step per phase (merged), counts for leaf fan-out, correct `state`.
- MUST NOT import `streamlit`. MUST NOT read patient text. MUST NOT raise on unknown `event_type`/`agent_type` (→ generic step).
- Idempotent: calling repeatedly as the buffer grows yields a monotonically-advancing step list (no flicker/reorder).

**Phase mapping** (from research.md): INTAKE→analyze, RESEARCH_COORDINATOR→research, SOURCE_READER→read_sources (counted), RESEARCH_AGGREGATOR→aggregate, TRIALS*/TRIAL_READER→trials (counted), CROSS_INDICATION_COORD/KG_TRAVERSAL/HYPOTHESIS→off_label, REPORT_SYNTHESIZER→summarize, else→other.

## 2. Render (`app/components/thinking_trace.py`) — Streamlit only

```python
def render_live(steps: list[TraceStep]) -> None:
    """Render the in-progress thinking block: one st.status(state='running')
    whose label is the current step; prior steps listed as done/failed lines.
    Called each fragment tick inside an assistant st.chat_message."""

def render_static(steps: list[TraceStep], state: str) -> None:
    """Render a completed run's thinking block: st.status(summary, state=...,
    expanded=False) listing all steps. Rendered in the history loop (NOT in a
    run_every fragment) so the user's expand/collapse persists."""
```

**Contract**:
- `render_static` MUST be re-render-stable: collapsing/expanding by the user persists across script reruns (no forced `expanded` reset every tick) — fixes the reported bug (FR-008, SC-005).
- Summary label reflects final state: completed → `"Thought through {N} steps"`; failed → `"Stopped during {failing step label}"`.
- On a failed step, the error line text comes from the failing event's payload (`AGENT_FAILED`/`RUN_FAILED` → `payload["error"]`), surfaced verbatim but never mixed with patient input (F3, Principle V).
- Each step shows an icon by state (running/done/failed) + its `label`; counts already baked into `label`.
- No raw enum identifiers ever rendered (FR-003, SC-002).

## 3. Integration points (`app/main.py`)

- During `run_status == "running"`: render `st.chat_message("assistant")` → `@st.fragment(run_every="0.7s")` → drain events → `derive_steps` → `render_live`. On done: append message `{role, content:"", report, steps, trace_state}` and rerun.
- History loop: for assistant messages with `steps`, call `render_static(msg["steps"], msg["trace_state"])` **above** `report_view.render(msg["report"])`.
- Sidebar: no trace; "New case" only.

## 4. Negative contracts (removals)

- `app/components/agent_trace.py` no longer exists; nothing imports it.
- `app/main.py` has no `_render_sidebar_trace` and no "Agent activity" sidebar subheader.
- No session-state key is written but never read (audit `events`, `report`).
