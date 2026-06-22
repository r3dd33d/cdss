from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.patient import PatientProfile
from cdss.core.models.trial import ClinicalTrial, TrialSummary
from cdss.integrations.clinical_trials import fetch_study, study_text
from cdss.llm.client import LLMClient
from cdss.llm.prompts.trial_reader import TRIAL_READER_PROMPT
from cdss.observability.run_context import RunContext
from cdss.sources.registry import SourceRegistry


class TrialReaderTask(AgentTask):
    trial: ClinicalTrial
    profile: PatientProfile


class TrialReaderAgent(BaseAgent):
    def __init__(self, llm: LLMClient, source_registry: SourceRegistry, **_) -> None:
        self._llm = llm
        self._registry = source_registry

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: TrialReaderTask = task  # type: ignore[assignment]
        trial = t.trial
        study = await fetch_study(trial.nct_id)
        if not study:
            raise RuntimeError(f"Could not fetch study {trial.nct_id}")

        text = study_text(study, max_chars=self._registry.fetch.max_content_chars)
        biomarkers = ", ".join(
            f"{b.gene} ({b.variant_type})" for b in t.profile.biomarkers
        ) or "None stated"
        prompt = TRIAL_READER_PROMPT.format(
            condition=t.profile.condition,
            stage=t.profile.stage,
            biomarkers=biomarkers,
            prior_therapies=", ".join(t.profile.prior_therapies) or "None",
            study_text=text,
        )
        excerpt = self._llm.chat(prompt, max_tokens=1024)
        summary = TrialSummary(
            nct_id=trial.nct_id,
            title=trial.title,
            phase=trial.phase,
            status=trial.status,
            url=trial.url,
            relevant_excerpt=excerpt,
            patient_fit_notes=excerpt[:300],
            confidence=0.7,
            agent_run_id=ctx.run_id,
        )
        return AgentResult(run_id=ctx.run_id, data=summary)
