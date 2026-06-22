import asyncio

from pydantic import BaseModel, Field

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.trials.trial_reader_agent import TrialReaderTask
from cdss.core.enums import AgentType
from cdss.core.models.patient import PatientProfile
from cdss.core.models.trial import ClinicalTrial, TrialSummary
from cdss.integrations.clinical_trials import fetch_trials, rank_trials
from cdss.observability.run_context import RunContext
from cdss.sources.registry import SourceRegistry


class TrialsCoordinatorTask(AgentTask):
    profile: PatientProfile


class TrialsCoordinatorResult(BaseModel):
    clinical_trials: list[ClinicalTrial] = Field(default_factory=list)
    trial_summaries: list[TrialSummary] = Field(default_factory=list)
    trials_matched_count: int = 0
    validation_flags: list[str] = Field(default_factory=list)


class TrialsCoordinatorAgent(BaseAgent):
    def __init__(self, source_registry: SourceRegistry, factory=None, **_) -> None:
        self._registry = source_registry
        self._factory = factory

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: TrialsCoordinatorTask = task  # type: ignore[assignment]
        cfg = self._registry.trials
        genes = [b.gene for b in t.profile.biomarkers if b.gene]

        trials, error = await fetch_trials(
            t.profile.condition,
            genes,
            max_results=cfg.max_search_results,
        )
        flags: list[str] = []
        if error:
            flags.append(error)

        matched_count = len(trials)
        ranked = rank_trials(
            trials,
            t.profile,
            limit=cfg.max_readers,
            recruiting_boost=cfg.rank_recruiting_boost,
        )

        sem = asyncio.Semaphore(cfg.max_readers)

        async def _read(trial: ClinicalTrial) -> TrialSummary | None:
            async with sem:
                reader_task = TrialReaderTask(trial=trial, profile=t.profile)
                try:
                    result = await self._factory.spawn(
                        AgentType.TRIAL_READER, reader_task, parent_run_id=ctx.run_id
                    )
                    return result.data
                except Exception as exc:
                    flags.append(f"Trial reader failed for {trial.nct_id}: {exc}")
                    return None

        summaries: list[TrialSummary | None] = await asyncio.gather(
            *[_read(tr) for tr in ranked]
        )
        data = TrialsCoordinatorResult(
            clinical_trials=ranked,
            trial_summaries=[s for s in summaries if s is not None],
            trials_matched_count=matched_count,
            validation_flags=flags,
        )
        return AgentResult(run_id=ctx.run_id, data=data, validation_flags=flags)
