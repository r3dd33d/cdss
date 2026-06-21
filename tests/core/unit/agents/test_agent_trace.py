"""Unit tests for agent_trace component logic (no Streamlit runtime needed)."""
from cdss.core.enums import AgentType, EventType
from cdss.observability.events import AgentEvent


def _evt(event_type, run_id, parent_run_id=None, agent_type=None, label="", duration_ms=None):
    return AgentEvent.build(
        event_type, run_id,
        parent_run_id=parent_run_id,
        agent_type=agent_type,
        label=label,
        duration_ms=duration_ms,
    )


def _build_node_dict(events):
    """Mirror the node-building logic from agent_trace.render."""
    from cdss.core.enums import EventType
    STATUS_MAP = {
        EventType.AGENT_COMPLETED: "complete",
        EventType.AGENT_FAILED: "error",
        EventType.AGENT_STARTED: "running",
        EventType.AGENT_SPAWNED: "running",
    }
    nodes = {}
    for e in events:
        if e.run_id not in nodes:
            nodes[e.run_id] = {
                "label": e.label or str(e.agent_type or e.event_type),
                "state": "running",
                "parent": e.parent_run_id,
                "duration_ms": None,
            }
        state = STATUS_MAP.get(e.event_type)
        if state:
            nodes[e.run_id]["state"] = state
        if e.duration_ms:
            nodes[e.run_id]["duration_ms"] = e.duration_ms
    return nodes


def test_spawned_node_has_parent():
    events = [
        _evt(EventType.AGENT_SPAWNED, "child1", parent_run_id="root", label="IntakeAgent"),
    ]
    nodes = _build_node_dict(events)
    assert nodes["child1"]["parent"] == "root"


def test_completed_node_state():
    events = [
        _evt(EventType.AGENT_SPAWNED, "c1", parent_run_id="root"),
        _evt(EventType.AGENT_COMPLETED, "c1", duration_ms=1200),
    ]
    nodes = _build_node_dict(events)
    assert nodes["c1"]["state"] == "complete"
    assert nodes["c1"]["duration_ms"] == 1200


def test_failed_node_state():
    events = [
        _evt(EventType.AGENT_SPAWNED, "c2", parent_run_id="root"),
        _evt(EventType.AGENT_FAILED, "c2"),
    ]
    nodes = _build_node_dict(events)
    assert nodes["c2"]["state"] == "error"


def test_parallel_readers_all_appear():
    events = [
        _evt(EventType.AGENT_SPAWNED, f"reader{i}", parent_run_id="coord", label=f"Source {i}")
        for i in range(3)
    ]
    nodes = _build_node_dict(events)
    assert len(nodes) == 3
    assert all(n["parent"] == "coord" for n in nodes.values())


def test_mixed_success_and_failure():
    events = [
        _evt(EventType.AGENT_SPAWNED, "r1", parent_run_id="coord"),
        _evt(EventType.AGENT_COMPLETED, "r1", duration_ms=300),
        _evt(EventType.AGENT_SPAWNED, "r2", parent_run_id="coord"),
        _evt(EventType.AGENT_FAILED, "r2"),
    ]
    nodes = _build_node_dict(events)
    assert nodes["r1"]["state"] == "complete"
    assert nodes["r2"]["state"] == "error"
