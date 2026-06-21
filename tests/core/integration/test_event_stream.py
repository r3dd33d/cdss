"""Integration: failing source emits AGENT_FAILED but run still completes."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.factory import AgentFactory
from cdss.agents.registry import AgentRegistry
from cdss.core.enums import AgentType, EventType
from cdss.core.exceptions import FetchError
from cdss.observability.event_bus import EventBus
from cdss.observability.trace_store import TraceStore


class _FailingReader(BaseAgent):
    async def run(self, task: AgentTask, ctx) -> AgentResult:
        raise FetchError("timeout")


class _OkReader(BaseAgent):
    async def run(self, task: AgentTask, ctx) -> AgentResult:
        return AgentResult(run_id=ctx.run_id, data="summary")


@pytest.mark.asyncio
async def test_isolated_failure_does_not_abort_batch():
    store = TraceStore()
    bus = EventBus(store)
    reg = AgentRegistry()
    reg.register(AgentType.SOURCE_READER, _OkReader)

    factory = AgentFactory(reg, bus)

    results = []
    errors = []
    for i in range(3):
        cls = _FailingReader if i == 1 else _OkReader
        reg._map[AgentType.SOURCE_READER] = cls
        try:
            r = await factory.spawn(AgentType.SOURCE_READER, AgentTask(), parent_run_id="coord")
            results.append(r)
        except FetchError:
            errors.append(i)

    assert len(results) == 2
    assert len(errors) == 1

    # All events (across all child run_ids) should include both completed and failed.
    all_types = []
    for run_id in store._store:
        all_types.extend(e.event_type for e in store.get(run_id))

    assert EventType.AGENT_COMPLETED in all_types
    assert EventType.AGENT_FAILED in all_types


@pytest.mark.asyncio
async def test_run_completed_is_terminal():
    """Verify bus.close() sends a single None sentinel terminating the stream."""
    store = TraceStore()
    bus = EventBus(store)
    q = bus.subscribe("run1")
    bus.close("run1")
    sentinel = q.get_nowait()
    assert sentinel is None
    assert q.empty()
