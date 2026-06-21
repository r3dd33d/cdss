# Tasks: Chat UI Layout Redesign

**Input**: Design documents from `/specs/002-chat-ui-layout/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓  
**Scope**: Presentation-only changes in `app/` — no `cdss/` modifications.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Layout restructure (US1 + US2 — P1)

**Goal**: Full-width chat with bottom input; agent activity in sidebar.

- [x] T001 [US1] Refactor `app/main.py`: remove `st.columns([3, 2])`; render messages and suggestions in full main column; place `st.chat_input` last with no widgets after it.
- [x] T002 [US2] Move live trace fragment and static trace rendering into `with st.sidebar:` block in `app/main.py`; preserve `@st.fragment(run_every="0.7s")` drain/completion logic.
- [x] T003 [US2] Add sidebar empty-state caption and ":material/psychology: Agent activity" heading per design skill conventions.

**Checkpoint**: Manual — input at bottom, trace in sidebar only (quickstart US1–US2).

---

## Phase 2: Example prompts (US3 — P2)

**Goal**: Uniform-sized example controls that submit full clinical text.

- [x] T004 [US3] Refactor `app/components/suggestions.py`: tuple list of (short label, full text); render via `st.pills`; return full text on selection.
- [x] T005 [P] [US3] Hide suggestions once `messages` non-empty (already gated in main.py — verify).

**Checkpoint**: Manual — equal pill sizes; full text submitted (quickstart US3).

---

## Phase 3: Session controls & polish (US4 — P3)

**Goal**: New case in sidebar; compact disclaimer.

- [x] T006 [US4] Move "New case" button to sidebar footer in `app/main.py`; use Material icon label.
- [x] T007 [P] [US4] Optional compact disclaimer in `app/components/disclaimer.py` (keep warning, reduce visual weight if needed).

**Checkpoint**: Manual — reset works from sidebar; disclaimer visible (quickstart US4).

---

## Phase 4: Polish & regression

- [x] T008 [POLISH] Run `make test` and `make guards` — all pass unchanged.
- [x] T009 [POLISH] Walk through `quickstart.md` checklist; mark items complete.

**Checkpoint**: Feature ready to merge to `main`.

## Dependencies

```text
T001 → T002 → T003 → T004 → T006 → T008
         T005 (parallel after T004)
         T007 (parallel after T006)
```

## MVP scope

Phases 1–2 (T001–T005) deliver the core layout fix. Phase 3 is polish.
