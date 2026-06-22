"""Friendly phrasing for the agent activity stream. Streamlit-free so it stays
unit-testable; the headless core is never imported into the UI the other way."""
from __future__ import annotations

from dataclasses import dataclass

from cdss.core.enums import AgentType, EventType
from cdss.observability.events import AgentEvent

# Phase keys in pipeline order; earlier phases are marked done when a later starts.
_PHASE_ORDER = [
    "start", "analyze", "research", "read_sources",
    "aggregate", "trials", "off_label", "summarize", "other",
]

# Agent type -> (phase key, default friendly label).
_AGENT_PHASE: dict[AgentType, tuple[str, str]] = {
    AgentType.INTAKE: ("analyze", "Analyzing your question"),
    AgentType.RESEARCH_COORDINATOR: ("research", "Searching guideline sources"),
    AgentType.SOURCE_READER: ("read_sources", "Reading sources"),
    AgentType.RESEARCH_AGGREGATOR: ("aggregate", "Synthesizing source findings"),
    AgentType.TRIALS: ("trials", "Checking clinical trials"),
    AgentType.TRIALS_COORDINATOR: ("trials", "Checking clinical trials"),
    AgentType.TRIAL_READER: ("trials", "Reviewing clinical trials"),
    AgentType.TRIAL_AGGREGATOR: ("trials", "Checking clinical trials"),
    AgentType.CROSS_INDICATION_COORD: ("off_label", "Exploring off-label options"),
    AgentType.KG_TRAVERSAL: ("off_label", "Exploring off-label options"),
    AgentType.HYPOTHESIS: ("off_label", "Exploring off-label options"),
    AgentType.REPORT_SYNTHESIZER: ("summarize", "Summarizing findings"),
}


def _sources_label(n: int) -> str:
    return f"Reading {n} source{'s' if n != 1 else ''}"


def _trials_label(n: int) -> str:
    return f"Reviewing {n} clinical trial{'s' if n != 1 else ''}"


# Leaf agents whose spawn count is meaningful fan-out.
_COUNT_LABEL = {
    AgentType.SOURCE_READER: _sources_label,
    AgentType.TRIAL_READER: _trials_label,
}


@dataclass
class TraceStep:
    phase: str
    label: str
    count: int | None = None
    state: str = "running"   # running | done | failed
    detail: str | None = None   # error text on failure


def _order(phase: str) -> int:
    return _PHASE_ORDER.index(phase) if phase in _PHASE_ORDER else len(_PHASE_ORDER)


def derive_steps(events: list[AgentEvent]) -> list[TraceStep]:
    """Group a run's events into ordered, friendly steps with counts and state.
    Pure and idempotent; reads only event/agent types and counts, never patient text."""
    steps: dict[str, TraceStep] = {}

    def ensure(phase: str, label: str) -> TraceStep:
        step = steps.get(phase)
        if step is None:
            step = TraceStep(phase=phase, label=label)
            steps[phase] = step
        return step

    def advance_to(phase: str) -> None:
        idx = _order(phase)
        for s in steps.values():
            if s.state == "running" and _order(s.phase) < idx:
                s.state = "done"

    for e in events:
        et = e.event_type
        if et == EventType.RUN_STARTED:
            ensure("start", "Starting research")
        elif et in (EventType.AGENT_SPAWNED, EventType.AGENT_STARTED):
            phase, label = _AGENT_PHASE.get(e.agent_type, ("other", "Working…"))
            advance_to(phase)
            step = ensure(phase, label)
            step.state = "running"
            if et == EventType.AGENT_SPAWNED and e.agent_type in _COUNT_LABEL:
                step.count = (step.count or 0) + 1
                step.label = _COUNT_LABEL[e.agent_type](step.count)
        elif et == EventType.AGENT_COMPLETED:
            phase, _ = _AGENT_PHASE.get(e.agent_type, ("other", ""))
            # Single-agent phases finish on completion; counted fan-out phases
            # finish when the next phase starts or the run ends.
            if phase in steps and steps[phase].count is None:
                steps[phase].state = "done"
        elif et == EventType.AGENT_FAILED:
            phase, label = _AGENT_PHASE.get(e.agent_type, ("other", "Working…"))
            step = ensure(phase, label)
            step.state = "failed"
            step.detail = e.payload.get("error")
        elif et == EventType.RUN_COMPLETED:
            for s in steps.values():
                if s.state == "running":
                    s.state = "done"
        elif et == EventType.RUN_FAILED:
            running = [s for s in steps.values() if s.state == "running"]
            target = running[-1] if running else (list(steps.values())[-1] if steps else None)
            if target:
                target.state = "failed"
                target.detail = target.detail or e.payload.get("error")

    return sorted(steps.values(), key=lambda s: _order(s.phase))
