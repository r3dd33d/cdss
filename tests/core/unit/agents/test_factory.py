import pytest

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.factory import AgentFactory
from cdss.agents.registry import AgentRegistry
from cdss.core.enums import AgentType, EventType
from cdss.observability.event_bus import EventBus
from cdss.observability.run_context import RunContext
from cdss.observability.trace_store import TraceStore


class _OkAgent(BaseAgent):
    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        return AgentResult(run_id=ctx.run_id, data="ok")


class _FailAgent(BaseAgent):
    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        raise ValueError("boom")


def _setup(agent_cls: type) -> tuple[AgentFactory, EventBus]:
    reg = AgentRegistry()
    reg.register(AgentType.INTAKE, agent_cls)
    store = TraceStore()
    bus = EventBus(store)
    factory = AgentFactory(reg, bus)
    return factory, bus


@pytest.mark.asyncio
async def test_spawn_emits_lifecycle_events():
    reg = AgentRegistry()
    reg.register(AgentType.INTAKE, _OkAgent)
    store = TraceStore()
    bus = EventBus(store)
    factory = AgentFactory(reg, bus)

    result = await factory.spawn(AgentType.INTAKE, AgentTask(), parent_run_id="run1")
    assert result.data == "ok"

    # Events are stored under the child run_id; check via trace store.
    all_events = store.get(result.run_id)
    types = [e.event_type for e in all_events]
    assert EventType.AGENT_SPAWNED in types
    assert EventType.AGENT_STARTED in types
    assert EventType.AGENT_COMPLETED in types


@pytest.mark.asyncio
async def test_spawn_sets_parent_run_id():
    reg = AgentRegistry()
    reg.register(AgentType.INTAKE, _OkAgent)
    store = TraceStore()
    bus = EventBus(store)
    factory = AgentFactory(reg, bus)

    result = await factory.spawn(AgentType.INTAKE, AgentTask(), parent_run_id="parent_run")
    all_events = store.get(result.run_id)
    spawned = [e for e in all_events if e.event_type == EventType.AGENT_SPAWNED]
    assert spawned[0].parent_run_id == "parent_run"


@pytest.mark.asyncio
async def test_spawn_emits_failed_on_exception():
    reg = AgentRegistry()
    reg.register(AgentType.INTAKE, _FailAgent)
    store = TraceStore()
    bus = EventBus(store)
    factory = AgentFactory(reg, bus)

    with pytest.raises(ValueError):
        result = await factory.spawn(AgentType.INTAKE, AgentTask(), parent_run_id="run_fail")

    # Find the failed agent's run_id from any stored events.
    all_run_ids = [k for k in store._store]
    types = []
    for rid in all_run_ids:
        types.extend(e.event_type for e in store.get(rid))
    assert EventType.AGENT_FAILED in types
    assert EventType.AGENT_COMPLETED not in types
