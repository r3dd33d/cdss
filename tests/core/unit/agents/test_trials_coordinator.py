import pytest
from unittest.mock import AsyncMock, MagicMock

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.trials.coordinator_agent import TrialsCoordinatorAgent, TrialsCoordinatorTask
from cdss.core.enums import AgentType
from cdss.core.models.patient import PatientProfile, Biomarker
from cdss.core.models.trial import ClinicalTrial, TrialSummary
from cdss.observability.run_context import RunContext
from cdss.sources.registry import (
    SourceRegistry, SearchConfig, FetchConfig, LLMConfig, SiteConfig, TrialsConfig,
)


def _registry(max_readers: int = 5) -> SourceRegistry:
    return SourceRegistry(
        sites=[SiteConfig(id="nccn", domain="nccn.org", priority=1, enabled=True)],
        search=SearchConfig(
            provider="serper", top_k_per_site=1, max_total_sources=5,
            query_template="{condition}",
        ),
        fetch=FetchConfig(timeout_seconds=5, max_content_chars=1000, user_agent="test"),
        llm=LLMConfig(
            provider="groq", max_tokens_intake=512, max_tokens_source_reader=512,
            max_tokens_synthesizer=1024, model_preference=["llama3-8b-8192"],
        ),
        trials=TrialsConfig(
            max_readers=max_readers, max_search_results=10, rank_recruiting_boost=2,
        ),
    )


def _trial(nct: str) -> ClinicalTrial:
    return ClinicalTrial(
        nct_id=nct, title=f"Trial {nct}", phase="PHASE2", status="RECRUITING",
        eligibility_summary="summary", url=f"https://clinicaltrials.gov/study/{nct}",
    )


class _MockFactory:
    def __init__(self, fail_nct: str | None = None):
        self.spawn_count = 0
        self.fail_nct = fail_nct

    async def spawn(self, agent_type, task, parent_run_id=None):
        self.spawn_count += 1
        nct = task.trial.nct_id
        if self.fail_nct and nct == self.fail_nct:
            raise RuntimeError("reader failed")
        summary = TrialSummary(
            nct_id=nct, title=task.trial.title, phase="PHASE2",
            status="RECRUITING", url=task.trial.url, relevant_excerpt="eligibility excerpt",
        )
        return AgentResult(run_id=f"reader_{nct}", data=summary)


@pytest.mark.asyncio
async def test_coordinator_spawns_up_to_five_readers(monkeypatch):
    trials = [_trial(f"NCT{i:03d}") for i in range(10)]
    monkeypatch.setattr(
        "cdss.agents.trials.coordinator_agent.fetch_trials",
        AsyncMock(return_value=(trials, None)),
    )
    factory = _MockFactory()
    agent = TrialsCoordinatorAgent(source_registry=_registry(5), factory=factory)
    profile = PatientProfile(condition="NSCLC", stage="III")
    result = await agent.run(TrialsCoordinatorTask(profile=profile), RunContext(run_id="c1"))
    assert factory.spawn_count == 5
    assert result.data.trials_matched_count == 10
    assert len(result.data.trial_summaries) == 5


@pytest.mark.asyncio
async def test_coordinator_spawns_three_when_three_hits(monkeypatch):
    trials = [_trial(f"NCT{i}") for i in range(3)]
    monkeypatch.setattr(
        "cdss.agents.trials.coordinator_agent.fetch_trials",
        AsyncMock(return_value=(trials, None)),
    )
    factory = _MockFactory()
    agent = TrialsCoordinatorAgent(source_registry=_registry(5), factory=factory)
    profile = PatientProfile(condition="NSCLC", stage="III")
    result = await agent.run(TrialsCoordinatorTask(profile=profile), RunContext(run_id="c2"))
    assert factory.spawn_count == 3
    assert len(result.data.trial_summaries) == 3


@pytest.mark.asyncio
async def test_coordinator_tolerates_reader_failure(monkeypatch):
    trials = [_trial("NCT001"), _trial("NCT002")]
    monkeypatch.setattr(
        "cdss.agents.trials.coordinator_agent.fetch_trials",
        AsyncMock(return_value=(trials, None)),
    )
    factory = _MockFactory(fail_nct="NCT001")
    agent = TrialsCoordinatorAgent(source_registry=_registry(5), factory=factory)
    profile = PatientProfile(condition="NSCLC", stage="III")
    result = await agent.run(TrialsCoordinatorTask(profile=profile), RunContext(run_id="c3"))
    assert len(result.data.trial_summaries) == 1
    assert any("NCT001" in f for f in result.validation_flags)
