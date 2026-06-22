from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.trial import TrialSummary
from cdss.llm.client import LLMClient
from cdss.llm.prompts.trial_aggregator import TRIAL_AGGREGATOR_PROMPT
from cdss.observability.run_context import RunContext


class TrialAggregatorTask(AgentTask):
    summaries: list[TrialSummary]
    matched_count: int
    condition: str
    stage: str


class TrialAggregatorAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: TrialAggregatorTask = task  # type: ignore[assignment]
        analyzed = len(t.summaries)
        if not t.summaries:
            text = (
                f"No clinical trials were deep-read for {t.condition} {t.stage}. "
                f"Search matched {t.matched_count} trial(s)."
            )
            return AgentResult(run_id=ctx.run_id, data=text)

        combined = "\n\n---\n\n".join(
            f"### {s.nct_id}: {s.title}\nPhase: {s.phase} | Status: {s.status}\n"
            f"{s.relevant_excerpt}"
            for s in t.summaries
        )
        prompt = TRIAL_AGGREGATOR_PROMPT.format(
            condition=t.condition,
            stage=t.stage,
            matched_count=t.matched_count,
            analyzed_count=analyzed,
            summaries=combined,
        )
        markdown = self._llm.chat(prompt, max_tokens=2048)
        header = (
            f"**{t.matched_count} trial(s) matched; {analyzed} analyzed in depth.**\n\n"
        )
        return AgentResult(run_id=ctx.run_id, data=header + markdown)
