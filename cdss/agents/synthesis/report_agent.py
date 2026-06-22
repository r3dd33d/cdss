from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.patient import PatientProfile
from cdss.core.models.report import FinalReport
from cdss.core.models.source import SourceSummary
from cdss.core.models.hypothesis import OffLabelHypothesis
from cdss.llm.client import LLMClient
from cdss.llm.prompts.synthesizer import DISCLAIMER, SYNTHESIZER_PROMPT
from cdss.observability.run_context import RunContext


class SynthesizerTask(AgentTask):
    profile: PatientProfile
    standard_care: str
    source_summaries: list[SourceSummary]
    trials_aggregated: str
    trials_matched_count: int
    trials_analyzed_count: int
    hypotheses: list[OffLabelHypothesis]
    validation_flags: list[str]


class ReportSynthesizerAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: SynthesizerTask = task  # type: ignore[assignment]
        prompt = SYNTHESIZER_PROMPT.format(
            trials_matched_count=t.trials_matched_count,
            trials_analyzed_count=t.trials_analyzed_count,
            hypotheses_count=len(t.hypotheses),
            disclaimer=DISCLAIMER,
            profile=t.profile.model_dump_json(),
            standard_care=t.standard_care or "Not retrieved.",
            trials_aggregated=t.trials_aggregated or "None found.",
            hypotheses="\n".join(h.model_dump_json() for h in t.hypotheses) or "None found.",
            flags=", ".join(t.validation_flags) or "None",
        )
        markdown = self._llm.chat(prompt, max_tokens=4096)

        if DISCLAIMER not in markdown:
            markdown += f"\n\n---\n\n{DISCLAIMER}"

        report = FinalReport(
            markdown=markdown,
            profile=t.profile,
            sources=[s.source for s in t.source_summaries],
            trials_count=t.trials_analyzed_count,
            trials_matched_count=t.trials_matched_count,
            trials_analyzed_count=t.trials_analyzed_count,
            hypotheses_count=len(t.hypotheses),
            validation_flags=t.validation_flags,
        )
        return AgentResult(run_id=ctx.run_id, data=report)
