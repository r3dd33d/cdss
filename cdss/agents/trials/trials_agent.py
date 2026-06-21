from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.config.settings import Settings
from cdss.core.models.patient import PatientProfile
from cdss.integrations.clinical_trials import fetch_trials
from cdss.observability.run_context import RunContext


class TrialsTask(AgentTask):
    profile: PatientProfile


class TrialsAgent(BaseAgent):
    def __init__(self, settings: Settings, **_) -> None:
        self._settings = settings

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: TrialsTask = task  # type: ignore[assignment]
        genes = [b.gene for b in t.profile.biomarkers]
        trials = await fetch_trials(
            condition=t.profile.condition,
            biomarker_genes=genes,
            base_url=self._settings.clinical_trials_base_url,
        )
        return AgentResult(run_id=ctx.run_id, data=trials)
