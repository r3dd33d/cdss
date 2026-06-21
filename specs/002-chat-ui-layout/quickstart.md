# Quickstart: Chat UI Layout Verification

**Feature**: 002-chat-ui-layout | **Branch**: `002-chat-ui-layout`

## Run the app

```bash
make run
# or: python -m streamlit run app/main.py
```

## Manual checklist

### US1 — Bottom-anchored input

- [ ] Open app; confirm message input is at the bottom of the viewport.
- [ ] Confirm no "New case" or other button appears below the input in the main area.
- [ ] Send a message; confirm input stays at bottom after report renders.

### US2 — Sidebar agent activity

- [ ] Start a run; confirm agent tree appears in the left sidebar only.
- [ ] Confirm main column is full-width chat (no second column).
- [ ] After completion, trace remains in sidebar.

### US3 — Uniform example prompts

- [ ] On empty state, confirm all three example controls are the same size.
- [ ] Click each; confirm full clinical text appears as user message (not truncated).

### US4 — Session controls

- [ ] Click "New case" in sidebar; confirm messages and trace reset.
- [ ] Confirm disclaimer still visible.

## Regression

```bash
make test
make guards
```

All existing tests must pass without modification to `cdss/`.
