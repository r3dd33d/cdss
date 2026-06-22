"""In-chat chain-of-thought block. Renders the agent activity as readable steps
inside the assistant turn (live while running, static once complete)."""
from __future__ import annotations

import streamlit as st

from app.components.trace_labels import TraceStep

_ICON = {"running": "🔵", "done": "✓", "failed": "✗"}


def _step_lines(steps: list[TraceStep]) -> None:
    for s in steps:
        st.write(f"{_ICON.get(s.state, '•')} {s.label}")
        if s.detail:
            st.caption(s.detail)


def render_live(steps: list[TraceStep]) -> None:
    """In-progress block: one running st.status labelled by the current step."""
    if not steps:
        st.status("Thinking…", state="running", expanded=True)
        return
    current = next((s for s in reversed(steps) if s.state == "running"), steps[-1])
    with st.status(current.label, state="running", expanded=True):
        _step_lines(steps)


def render_static(steps: list[TraceStep], state: str) -> None:
    """Completed-run block. Rendered outside any live fragment so the user's
    expand/collapse persists across reruns (no forced re-collapse)."""
    if not steps:
        return
    if state == "failed":
        failed = next((s for s in steps if s.state == "failed"), None)
        summary = f"Stopped during {failed.label.lower()}" if failed else "Run stopped"
        status_state = "error"
    else:
        summary = f"Thought through {len(steps)} steps"
        status_state = "complete"
    with st.status(summary, state=status_state, expanded=False):
        _step_lines(steps)
