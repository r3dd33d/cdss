# Implementation Plan: Chat UI Layout Redesign

**Branch**: `002-chat-ui-layout` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/002-chat-ui-layout/spec.md`

## Summary

Restructure the Streamlit chat UI to match familiar AI-assistant patterns: a
full-width main column for conversation (messages above, input anchored at the
bottom), agent activity relocated to the sidebar, uniformly sized example prompts
on the empty state, and session controls ("New case") in the sidebar. All changes
are confined to `app/` presentation code; the runner bridge, session state keys,
event model, and `cdss/` core remain unchanged.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Streamlit ≥1.35 (`st.chat_message`, `st.chat_input`, `st.sidebar`, `st.pills` or bordered containers, `st.fragment`, `st.status`)  
**Storage**: N/A (uses existing `st.session_state` from feature 001)  
**Testing**: Manual UI verification; existing pytest suite unchanged; optional `AppTest` smoke for layout wiring  
**Target Platform**: `streamlit run app/main.py` (desktop-first)  
**Project Type**: Single Streamlit app — UI-only diff in `app/`  
**Performance Goals**: Sidebar trace refresh at 0.7 s (unchanged); no regression in run latency  
**Constraints**: `cdss/` MUST NOT import streamlit; no new runner methods; `st.chat_input` MUST be last widget in main column  
**Scale/Scope**: 4 user stories; ~4 files touched; no new packages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|-----------|------------------------|
| **I. Deep Modules, Small Files** | Layout logic stays in `main.py`; chips and trace remain separate components. No file exceeds size limit. |
| **II. UI/Core Separation** | Zero changes to `cdss/`; runner_bridge API unchanged; import guard unaffected. |
| **III–VI** | N/A or unchanged — no LLM, factory, or pipeline changes. |
| **V. Research-Only Safety** | Disclaimer remains visible; compact styling only. |
| **VI. Surgical Changes** | Targeted edits to layout wiring and two components; no rewrites. |

**Result**: PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-chat-ui-layout/
├── spec.md
├── context.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-layout.md
└── tasks.md
```

### Source Code (changes only)

```text
app/
├── main.py                 # Remove columns; sidebar trace; chat_input last
├── components/
│   ├── suggestions.py      # Uniform chips (pills or fixed-height cards)
│   ├── agent_trace.py      # Sidebar-friendly compact rendering
│   └── disclaimer.py       # Optional compact banner
└── state/session.py        # Unchanged
```

**Structure Decision**: Presentation-only refactor within existing `app/` package.

## Phase 0: Research Decisions

See [research.md](./research.md). Key decisions:

1. Drop `st.columns([3, 2])` — use full main + `st.sidebar`.
2. Keep `@st.fragment(run_every="0.7s")` in sidebar for live trace.
3. Use `st.pills` with short labels mapping to full example strings for uniform chips.
4. Move "New case" to sidebar; nothing below `st.chat_input` in main column.

## Phase 1: Design Artifacts

- [data-model.md](./data-model.md) — session/UI entities (unchanged semantics)
- [contracts/ui-layout.md](./contracts/ui-layout.md) — layout zones and widget order
- [quickstart.md](./quickstart.md) — manual verification steps

## Complexity Tracking

> Empty — no constitution violations.
