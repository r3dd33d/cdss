# Implementation Plan: Inline Chain-of-Thought Agent Trace

**Branch**: `004-chat-thinking-trace` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-chat-thinking-trace/spec.md`

## Summary

Relocate the multi-agent pipeline's live progress from the collapsing sidebar chip into the chat thread, rendered as a readable, streaming "thinking" block within the assistant's turn. The core already emits all needed events (Principle IV); this is a **UI-only** change in `app/`. We add a pure labeling layer that groups raw events into ~5 readable phases with counts, a chat-embedded renderer, and we **remove the now-orphaned sidebar trace code and dead session state**.

## Technical Context

**Language/Version**: Python 3.11+ (repo runs 3.13)  
**Primary Dependencies**: Streamlit (UI only); consumes existing `cdss` event stream read-only  
**Storage**: N/A (in-memory session state; per-turn steps attached to chat messages)  
**Testing**: pytest — unit test the pure label/step-derivation function; UI smoke via `st.testing.AppTest` with a stubbed bridge (no real agents)  
**Target Platform**: Streamlit app (`app/main.py`), local + headless  
**Project Type**: Single Streamlit application (headless core `cdss/` + UI `app/`)  
**Performance Goals**: a new step visible within ~1s of the underlying activity (live fragment tick ≤ 0.7s)  
**Constraints**: `cdss/` MUST NOT import Streamlit; labeling layer stays Streamlit-free so it is unit-testable; no core/event-schema changes unless a count is genuinely missing  
**Scale/Scope**: ~3 UI modules touched/added; one removal of the sidebar trace section

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Deep modules, small files (<200/<400) | PASS | New `trace_labels.py` (pure, ~80 lines) and `thinking_trace.py` (render, ~80 lines) are small leaf modules. `agent_trace.py` is deleted, not grown. |
| II. UI/Core separation — Streamlit-only | PASS | All changes in `app/`. `cdss/` untouched. `trace_labels.derive_steps()` imports **no** Streamlit, so it is core-style testable; only `thinking_trace.py` touches `st.*`. |
| III. Free-model-first | PASS (N/A) | No LLM/model changes. |
| IV. Agents spawn via factory; everything emits events | PASS | We **consume** existing events read-only; emit nothing new. Verified payloads carry spawn/source/trial counts; if a count is missing, see Research R3. |
| V. Research-only safety | PASS | Disclaimer rendering unchanged. Steps are derived from `event_type`/`agent_type`/counts only — never raw patient text. Events already redact PII (`_PII_KEYS`); the labeling layer reads only non-PII fields. |
| VI. Surgical changes — minimal diffs | PASS (justified removal) | The sidebar trace deletion is **required relocation**, not churn — the same capability moves into chat. Documented in Removal Plan below. |
| VII. Short comments | PASS | New modules use one–two-sentence comments. |

**Result**: PASS — no violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/004-chat-thinking-trace/
├── spec.md              # Feature spec (done)
├── context.md           # Feature context (done)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (presentation entities)
├── quickstart.md        # Phase 1 output (manual verification)
├── contracts/
│   └── trace-ui.md      # Phase 1 output (UI/label contract)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
app/
├── main.py                      # MODIFY: remove sidebar trace; render live + static thinking block in chat turn
├── state/
│   └── session.py               # MODIFY: attach per-turn `steps` to assistant message; retire orphaned state
└── components/
    ├── agent_trace.py           # DELETE: replaced by thinking_trace.py
    ├── trace_labels.py          # ADD: pure event→step labeling (no Streamlit), grouped into phases + counts
    └── thinking_trace.py        # ADD: render thinking block inside st.chat_message (live + static)

tests/
└── app/
    └── unit/
        ├── test_trace_labels.py     # ADD: pure unit tests for derive_steps (synthetic event lists)
        └── test_thinking_trace.py   # ADD (optional): AppTest smoke with stubbed bridge
```

**Structure Decision**: Single Streamlit app. The friendly-phrasing logic is isolated in a Streamlit-free `trace_labels.py` (unit-testable like core), and all `st.*` rendering is isolated in `thinking_trace.py`. `main.py` orchestrates: live block during a run, static block per assistant turn afterward.

## Removal Plan (explicit — relocated UI parts)

The activity is **moving**, so its old home is deleted to avoid dead code (FR-001, user directive):

1. **`app/main.py`**
   - Delete `_render_sidebar_trace(handle)` entirely (lines ~38–69).
   - In the `with st.sidebar:` block, delete `st.subheader(":material/psychology: Agent activity")` and the `_render_sidebar_trace(...)` call. **Keep** the "New case" button and `st.divider()` (or move New case to the main column — see Research R4).
   - Move the live-trace fragment logic into the assistant turn render path (in the chat area), not the sidebar.
   - Clear the live event buffer in `_start_research_run()` when a run begins (F2 / FR-009 isolation), so consecutive same-session runs do not inherit prior steps.
   - On run completion, append the assistant message with **both** `report` and `steps` (derived from the run's events).

2. **`app/components/agent_trace.py`** — **DELETE** the file. Its `_STATUS_MAP` and tree-rendering are superseded by `trace_labels.derive_steps()` + `thinking_trace.render_*()`. Remove its import from `app/main.py` (`from app.components import agent_trace, …`).

3. **`app/state/session.py`** — audit and clean:
   - `events`: keep **only** as a transient live-accumulation buffer during a running pipeline; it is consumed into the message's `steps` on completion and cleared on `reset()`. If, after wiring per-turn `steps`, `events` is no longer read anywhere, remove it too (no orphaned state).
   - `report`: **verify usage** — `report_view` renders from `msg["report"]`, not `st.session_state.report`. If unread, remove this orphaned key (it is set in `main.py` but appears unused). `last_report` is read by `chat_bridge` routing → **keep**.

4. **Grep gate**: after edits, `grep -rn "agent_trace\|_render_sidebar_trace\|session_state.report\b" app/` must return only intended references (or none), confirming no orphaned imports/state.

## Complexity Tracking

> No constitution violations — section intentionally empty.
