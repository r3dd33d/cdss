from __future__ import annotations

import streamlit as st

from cdss.core.enums import EventType
from cdss.observability.events import AgentEvent

# Maps EventType to st.status state string.
_STATUS_MAP = {
    EventType.AGENT_COMPLETED: "complete",
    EventType.AGENT_FAILED: "error",
    EventType.AGENT_STARTED: "running",
    EventType.AGENT_SPAWNED: "running",
}


def render(events: list[AgentEvent]) -> None:
    """Render the agent spawn tree from a flat event list."""
    if not events:
        st.caption("Waiting for agents…")
        return

    # Build a node dict keyed by run_id.
    nodes: dict[str, dict] = {}
    for e in events:
        if e.run_id not in nodes:
            nodes[e.run_id] = {
                "label": e.label or (e.agent_type or e.event_type),
                "state": "running",
                "parent": e.parent_run_id,
                "duration_ms": None,
            }
        state = _STATUS_MAP.get(e.event_type)
        if state:
            nodes[e.run_id]["state"] = state
        if e.duration_ms:
            nodes[e.run_id]["duration_ms"] = e.duration_ms

    # Render root nodes then children (simple two-level tree for now).
    roots = [nid for nid, n in nodes.items() if not n["parent"]]
    for root_id in roots:
        n = nodes[root_id]
        dur = f" {n['duration_ms']}ms" if n["duration_ms"] else ""
        with st.status(f"{n['label']}{dur}", state=n["state"], expanded=False):
            children = [nid for nid, c in nodes.items() if c["parent"] == root_id]
            for cid in children:
                c = nodes[cid]
                cdur = f" {c['duration_ms']}ms" if c["duration_ms"] else ""
                icon = "✓" if c["state"] == "complete" else ("✗" if c["state"] == "error" else "●")
                st.write(f"{icon} {c['label']}{cdur}")
