from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.source import SourceSummary
from cdss.llm.client import LLMClient
from cdss.observability.run_context import RunContext


class AggregatorTask(AgentTask):
    summaries: list[SourceSummary]
    condition: str
    stage: str


class ResearchAggregatorAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: AggregatorTask = task  # type: ignore[assignment]
        if not t.summaries:
            return AgentResult(run_id=ctx.run_id, data="No guideline sources were retrieved.")

        combined = "\n\n".join(
            f"Source {i+1} ({s.source.site_id}):\n{s.relevant_excerpt}"
            for i, s in enumerate(t.summaries)
        )
        prompt = (
            f"Synthesize the following guideline excerpts into a concise standard-of-care "
            f"summary for {t.condition} {t.stage}. Keep it factual and cite sources by number.\n\n"
            f"{combined}"
        )
        summary = self._llm.chat(prompt, max_tokens=1024)
        return AgentResult(run_id=ctx.run_id, data=summary)
