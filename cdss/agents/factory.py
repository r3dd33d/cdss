import uuid
from datetime import datetime, timezone
from time import monotonic

from cdss.agents.base import AgentTask, AgentResult
from cdss.agents.registry import AgentRegistry
from cdss.core.enums import AgentType, EventType
from cdss.observability.event_bus import EventBus
from cdss.observability.events import AgentEvent
from cdss.observability.run_context import RunContext


class AgentFactory:
    """Sole path for creating and running agents; owns all lifecycle events."""

    def __init__(self, registry: AgentRegistry, bus: EventBus, **deps) -> None:
        self._registry = registry
        self._bus = bus
        self._deps = deps  # injected collaborators (llm, sources, knowledge, …)

    async def spawn(
        self,
        agent_type: AgentType,
        task: AgentTask,
        *,
        parent_run_id: str | None = None,
    ) -> AgentResult:
        run_id = f"agent_{uuid.uuid4().hex[:8]}"
        ctx = RunContext(run_id=run_id, parent_id=parent_run_id)

        self._bus.publish(AgentEvent.build(
            EventType.AGENT_SPAWNED, run_id,
            parent_run_id=parent_run_id, agent_type=agent_type,
            label=agent_type.value,
        ))
        self._bus.publish(AgentEvent.build(
            EventType.AGENT_STARTED, run_id, agent_type=agent_type,
        ))

        agent_cls = self._registry.get(agent_type)
        agent = agent_cls(**self._deps)
        start = monotonic()
        try:
            result = await agent.run(task, ctx)
            duration = int((monotonic() - start) * 1000)
            self._bus.publish(AgentEvent.build(
                EventType.AGENT_COMPLETED, run_id, agent_type=agent_type,
                duration_ms=duration,
            ))
            return result
        except Exception as exc:
            duration = int((monotonic() - start) * 1000)
            self._bus.publish(AgentEvent.build(
                EventType.AGENT_FAILED, run_id, agent_type=agent_type,
                duration_ms=duration, error=str(exc),
            ))
            raise
