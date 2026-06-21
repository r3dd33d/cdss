import asyncio

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.research.source_reader_agent import SourceReaderTask
from cdss.core.enums import AgentType
from cdss.core.models.source import SourceSummary
from cdss.observability.run_context import RunContext
from cdss.sources.search.base import AbstractSearchProvider
from cdss.sources.registry import SourceRegistry


class CoordinatorTask(AgentTask):
    question: str
    condition: str
    stage: str


class ResearchCoordinatorAgent(BaseAgent):
    def __init__(
        self,
        search: AbstractSearchProvider,
        source_registry: SourceRegistry,
        factory=None,
        **_,
    ) -> None:
        self._search = search
        self._registry = source_registry
        self._factory = factory

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: CoordinatorTask = task  # type: ignore[assignment]
        query = self._registry.search.query_template.format(
            condition=t.condition, stage=t.stage
        )
        refs = await self._search.search(query, self._registry.search.max_total_sources)

        sem = asyncio.Semaphore(self._registry.search.max_total_sources)

        async def _read(ref):
            async with sem:
                reader_task = SourceReaderTask(
                    source=ref,
                    question=t.question,
                    condition=t.condition,
                    stage=t.stage,
                )
                try:
                    result = await self._factory.spawn(
                        AgentType.SOURCE_READER, reader_task, parent_run_id=ctx.run_id
                    )
                    return result.data
                except Exception:
                    return None  # isolated failure

        summaries: list[SourceSummary | None] = await asyncio.gather(*[_read(r) for r in refs])
        return AgentResult(
            run_id=ctx.run_id,
            data=[s for s in summaries if s is not None],
        )
