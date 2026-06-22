"""Integration tests for trials deep-read pipeline (FR-002, SC-002, SC-003)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.factory import AgentFactory
from cdss.agents.intake.intake_agent import IntakeAgent
from cdss.agents.registry import AgentRegistry
from cdss.agents.research.aggregator_agent import ResearchAggregatorAgent
from cdss.agents.research.coordinator_agent import ResearchCoordinatorAgent
from cdss.agents.research.source_reader_agent import SourceReaderAgent
from cdss.agents.synthesis.report_agent import ReportSynthesizerAgent
from cdss.agents.cross_indication.coordinator_agent import CrossIndicationCoordinator
from cdss.agents.trials.coordinator_agent import TrialsCoordinatorResult
from cdss.agents.trials.aggregator_agent import TrialAggregatorAgent
from cdss.core.enums import AgentType, EventType
from cdss.core.models.trial import TrialSummary
from cdss.knowledge.graph import loader
from cdss.llm.prompts.synthesizer import DISCLAIMER
from cdss.observability.event_bus import EventBus
from cdss.observability.trace_store import TraceStore
from cdss.pipeline.state import PipelineState
from cdss.pipeline.workflow import build_graph
from cdss.sources.registry import (
    SourceRegistry, SearchConfig, FetchConfig, LLMConfig, SiteConfig, TrialsConfig,
)


def _mock_llm(responses: dict[str, str]) -> MagicMock:
    llm = MagicMock()
    def _chat(prompt, max_tokens=1024):
        for key, val in responses.items():
            if key in prompt:
                return val
        return responses.get("default", "Mocked LLM response.")
    llm.chat.side_effect = _chat
    return llm


def _registry() -> SourceRegistry:
    return SourceRegistry(
        sites=[SiteConfig(id="nccn", domain="nccn.org", priority=1, enabled=True)],
        search=SearchConfig(
            provider="serper", top_k_per_site=1, max_total_sources=2,
            query_template="{condition} {stage} standard of care",
        ),
        fetch=FetchConfig(timeout_seconds=5, max_content_chars=1000, user_agent="test"),
        llm=LLMConfig(
            provider="groq", max_tokens_intake=512, max_tokens_source_reader=512,
            max_tokens_synthesizer=1024, model_preference=["llama3-8b-8192"],
        ),
        trials=TrialsConfig(max_readers=5, max_search_results=10, rank_recruiting_boost=2),
    )


class _MockTrialsCoordinator(BaseAgent):
    def __init__(self, factory=None, **_) -> None:
        self._factory = factory

    async def run(self, task: AgentTask, ctx) -> AgentResult:
        from cdss.core.models.trial import ClinicalTrial
        trial = ClinicalTrial(
            nct_id="NCT999", title="HER2 Trial", phase="PHASE3", status="RECRUITING",
            eligibility_summary="Adults with HER2+", url="https://clinicaltrials.gov/study/NCT999",
        )
        summary = TrialSummary(
            nct_id="NCT999", title="HER2 Trial", phase="PHASE3", status="RECRUITING",
            url=trial.url,
            relevant_excerpt="Eligibility: HER2-positive breast cancer patients.",
        )
        if self._factory:
            reader_task = MagicMock()
            reader_task.trial = trial
            await self._factory.spawn(AgentType.TRIAL_READER, reader_task, parent_run_id=ctx.run_id)
        data = TrialsCoordinatorResult(
            clinical_trials=[trial],
            trial_summaries=[summary],
            trials_matched_count=10,
        )
        return AgentResult(run_id=ctx.run_id, data=data)


class _MockTrialReader(BaseAgent):
    def __init__(self, **_) -> None:
        pass

    async def run(self, task: AgentTask, ctx) -> AgentResult:
        summary = TrialSummary(
            nct_id="NCT999", title="HER2 Trial", phase="PHASE3", status="RECRUITING",
            url="https://clinicaltrials.gov/study/NCT999",
            relevant_excerpt="Eligibility criteria excerpt.",
        )
        return AgentResult(run_id=ctx.run_id, data=summary)


def _build_factory(llm, src_reg, fetcher, mock_search):
    store = TraceStore()
    bus = EventBus(store)
    reg = AgentRegistry()
    deps = dict(llm=llm, fetcher=fetcher, search=mock_search, source_registry=src_reg)
    reg.register(AgentType.INTAKE, IntakeAgent)
    reg.register(AgentType.SOURCE_READER, SourceReaderAgent)
    reg.register(AgentType.RESEARCH_AGGREGATOR, ResearchAggregatorAgent)
    reg.register(AgentType.TRIAL_READER, _MockTrialReader)
    reg.register(AgentType.TRIAL_AGGREGATOR, TrialAggregatorAgent)
    reg.register(AgentType.CROSS_INDICATION_COORD, CrossIndicationCoordinator)
    reg.register(AgentType.REPORT_SYNTHESIZER, ReportSynthesizerAgent)
    factory = AgentFactory(reg, bus, **deps)
    reg.register(AgentType.RESEARCH_COORDINATOR,
                 lambda **kw: ResearchCoordinatorAgent(**kw, factory=factory))
    reg.register(AgentType.TRIALS_COORDINATOR,
                 lambda **kw: _MockTrialsCoordinator(**kw, factory=factory))
    return factory, bus, store


@pytest.mark.asyncio
async def test_empty_condition_skips_trial_readers(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)
    profile_json = json.dumps({
        "condition": "", "stage": "",
        "biomarkers": [], "current_medications": [], "prior_therapies": [],
    })
    llm = _mock_llm({"Extract structured": profile_json, "default": f"Report.\n\n{DISCLAIMER}"})
    src_reg = _registry()
    fetcher = AsyncMock()
    mock_search = AsyncMock()
    mock_search.search.return_value = []
    factory, _, _ = _build_factory(llm, src_reg, fetcher, mock_search)
    graph = build_graph(factory)
    state = PipelineState(run_id="empty_cond", raw_input="I feel tired sometimes.")
    final = await graph.ainvoke(state)
    flags = final["validation_flags"] if isinstance(final, dict) else final.validation_flags
    assert any("no condition" in f.lower() for f in flags)


@pytest.mark.asyncio
async def test_trials_read_in_report_with_counts(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)
    profile_json = json.dumps({
        "condition": "breast cancer", "stage": "IV",
        "biomarkers": [{"gene": "HER2", "variant_type": "Amplification", "details": ""}],
        "current_medications": [], "prior_therapies": [],
    })
    llm = _mock_llm({
        "Extract structured": profile_json,
        "Merge the following clinical trial": "**10 trial(s) matched; 1 analyzed in depth.**\nEligibility: HER2+",
        "default": f"## Clinical Trials\n10 matched; 1 analyzed.\nEligibility excerpt.\n\n{DISCLAIMER}",
    })
    src_reg = _registry()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = b"<p>Guidelines text.</p>"
    from cdss.core.models.source import SourceRef
    mock_search = AsyncMock()
    mock_search.search.return_value = [
        SourceRef(url="https://nccn.org/bc", title="NCCN BC", site_id="nccn", rank=1)
    ]
    factory, _, _ = _build_factory(llm, src_reg, fetcher, mock_search)
    graph = build_graph(factory)
    state = PipelineState(run_id="trials_run", raw_input="HER2+ metastatic breast cancer")
    final = await graph.ainvoke(state)
    report = final["final_report"] if isinstance(final, dict) else final.final_report
    matched = final["trials_matched_count"] if isinstance(final, dict) else final.trials_matched_count
    assert matched == 10
    assert "eligibility" in report.lower() or "HER2" in report


@pytest.mark.asyncio
async def test_trace_includes_trial_reader_and_aggregator(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)
    profile_json = json.dumps({
        "condition": "NSCLC", "stage": "III",
        "biomarkers": [], "current_medications": [], "prior_therapies": [],
    })
    llm = _mock_llm({"Extract structured": profile_json, "default": f"R\n\n{DISCLAIMER}"})
    src_reg = _registry()
    fetcher = AsyncMock()
    mock_search = AsyncMock()
    mock_search.search.return_value = []
    factory, bus, store = _build_factory(llm, src_reg, fetcher, mock_search)
    graph = build_graph(factory)
    state = PipelineState(run_id="trace_run", raw_input="Stage III NSCLC")
    await graph.ainvoke(state)

    agent_types = []
    for run_id in store._store:
        for e in store.get(run_id):
            if e.agent_type:
                agent_types.append(e.agent_type)

    assert AgentType.TRIAL_READER in agent_types
    assert AgentType.TRIAL_AGGREGATOR in agent_types
    assert AgentType.TRIALS_COORDINATOR in agent_types
