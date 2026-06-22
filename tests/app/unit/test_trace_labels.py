"""Unit tests for the Streamlit-free trace labeling layer (feature 004)."""
from cdss.core.enums import AgentType, EventType
from cdss.observability.events import AgentEvent

from app.components.trace_labels import derive_steps


def _ev(event_type, agent_type=None, **payload):
    return AgentEvent.build(event_type, "run_1", agent_type=agent_type, **payload)


def _labels(steps):
    return [s.label for s in steps]


def test_ordered_readable_steps_no_raw_enums():
    events = [
        _ev(EventType.RUN_STARTED),
        _ev(EventType.AGENT_SPAWNED, AgentType.INTAKE),
        _ev(EventType.AGENT_STARTED, AgentType.INTAKE),
        _ev(EventType.AGENT_COMPLETED, AgentType.INTAKE),
        _ev(EventType.AGENT_SPAWNED, AgentType.REPORT_SYNTHESIZER),
        _ev(EventType.AGENT_COMPLETED, AgentType.REPORT_SYNTHESIZER),
        _ev(EventType.RUN_COMPLETED),
    ]
    steps = derive_steps(events)
    labels = _labels(steps)
    assert "Analyzing your question" in labels
    assert "Summarizing findings" in labels
    # No raw enum identifiers leak into any label (SC-002).
    raw = {e.value for e in EventType} | {a.value for a in AgentType}
    assert not any(token in lbl for lbl in labels for token in raw)
    # Earlier phase precedes later phase.
    assert labels.index("Analyzing your question") < labels.index("Summarizing findings")
    assert all(s.state == "done" for s in steps)


def test_unknown_agent_type_falls_back_to_generic():
    events = [_ev(EventType.AGENT_SPAWNED, AgentType.KG_TRAVERSAL)]
    # KG_TRAVERSAL is mapped (off_label); use a truly unmapped path via no agent_type.
    events = [_ev(EventType.AGENT_STARTED, None)]
    steps = derive_steps(events)
    assert _labels(steps) == ["Working…"]


def test_source_reader_fanout_count_in_label():
    events = [_ev(EventType.AGENT_SPAWNED, AgentType.SOURCE_READER) for _ in range(5)]
    steps = derive_steps(events)
    assert "Reading 5 sources" in _labels(steps)


def test_trial_reader_singular_plural():
    one = derive_steps([_ev(EventType.AGENT_SPAWNED, AgentType.TRIAL_READER)])
    assert "Reviewing 1 clinical trial" in _labels(one)
    three = derive_steps([_ev(EventType.AGENT_SPAWNED, AgentType.TRIAL_READER) for _ in range(3)])
    assert "Reviewing 3 clinical trials" in _labels(three)


def test_no_count_when_none_spawned():
    steps = derive_steps([_ev(EventType.AGENT_STARTED, AgentType.RESEARCH_COORDINATOR)])
    assert _labels(steps) == ["Searching guideline sources"]
    assert steps[0].count is None


def test_failure_marks_step_failed_with_detail():
    events = [
        _ev(EventType.AGENT_SPAWNED, AgentType.REPORT_SYNTHESIZER),
        _ev(EventType.AGENT_FAILED, AgentType.REPORT_SYNTHESIZER, error="boom"),
        _ev(EventType.RUN_FAILED, error="boom"),
    ]
    steps = derive_steps(events)
    failed = [s for s in steps if s.state == "failed"]
    assert failed and failed[0].detail == "boom"


def test_idempotent_as_buffer_grows():
    base = [
        _ev(EventType.RUN_STARTED),
        _ev(EventType.AGENT_SPAWNED, AgentType.INTAKE),
    ]
    grown = base + [_ev(EventType.AGENT_SPAWNED, AgentType.SOURCE_READER) for _ in range(2)]
    s1 = derive_steps(base)
    s2 = derive_steps(grown)
    # Existing phases keep their order; new phase appends after.
    assert [s.phase for s in s2][: len(s1)] == [s.phase for s in s1]
    assert "Reading 2 sources" in _labels(s2)
