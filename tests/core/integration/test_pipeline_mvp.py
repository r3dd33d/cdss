"""MVP pipeline integration test with all external calls mocked."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.agents.factory import AgentFactory
from cdss.agents.intake.intake_agent import IntakeAgent
from cdss.agents.registry import AgentRegistry
from cdss.agents.research.aggregator_agent import ResearchAggregatorAgent
from cdss.agents.research.coordinator_agent import ResearchCoordinatorAgent
from cdss.agents.research.source_reader_agent import SourceReaderAgent
from cdss.agents.synthesis.report_agent import ReportSynthesizerAgent
from cdss.agents.trials.aggregator_agent import TrialAggregatorAgent
from cdss.agents.trials.coordinator_agent import TrialsCoordinatorResult
from cdss.agents.cross_indication.coordinator_agent import CrossIndicationCoordinator
from cdss.core.enums import AgentType
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
    """Return different responses based on prompt content."""
    llm = MagicMock()
    def _chat(prompt, max_tokens=1024):
        for key, val in responses.items():
            if key in prompt:
                return val
        return responses.get("default", "Mocked LLM response.")
    llm.chat.side_effect = _chat
    return llm


def _mock_registry() -> SourceRegistry:
    return SourceRegistry(
        sites=[SiteConfig(id="nccn", domain="nccn.org", priority=1, enabled=True)],
        search=SearchConfig(
            provider="serper", top_k_per_site=1, max_total_sources=2,
            query_template="{condition} {stage} standard of care",
        ),
        fetch=FetchConfig(timeout_seconds=5, max_content_chars=1000, user_agent="test"),
        llm=LLMConfig(
            provider="groq", max_tokens_intake=512, max_tokens_source_reader=512,
            max_tokens_synthesizer=1024,
            model_preference=["llama3-8b-8192"],
        ),
        trials=TrialsConfig(max_readers=5, max_search_results=10, rank_recruiting_boost=2),
    )


class _MockTrialsCoordinator(BaseAgent):
    def __init__(self, **_) -> None:
        pass

    async def run(self, task: AgentTask, ctx) -> AgentResult:
        return AgentResult(
            run_id=ctx.run_id,
            data=TrialsCoordinatorResult(trials_matched_count=0),
        )


@pytest.mark.asyncio
async def test_mvp_pipeline_produces_report_with_disclaimer(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)

    profile_json = json.dumps({
        "condition": "NSCLC", "stage": "III",
        "biomarkers": [{"gene": "EGFR", "variant_type": "exon 19 deletion", "details": ""}],
        "current_medications": ["osimertinib"],
        "prior_therapies": [],
    })

    llm = _mock_llm({
        "Extract structured": profile_json,
        "default": f"Standard care summary.\n\n{DISCLAIMER}",
    })

    src_reg = _mock_registry()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = b"<p>NSCLC standard guidelines text here.</p>"

    mock_search = AsyncMock()
    from cdss.core.models.source import SourceRef
    mock_search.search.return_value = [
        SourceRef(url="https://nccn.org/nsclc", title="NCCN NSCLC", site_id="nccn", rank=1)
    ]

    store = TraceStore()
    bus = EventBus(store)
    reg = AgentRegistry()
    deps = dict(llm=llm, fetcher=fetcher, search=mock_search, source_registry=src_reg)

    reg.register(AgentType.INTAKE, IntakeAgent)
    reg.register(AgentType.SOURCE_READER, SourceReaderAgent)
    reg.register(AgentType.RESEARCH_AGGREGATOR, ResearchAggregatorAgent)
    reg.register(AgentType.TRIALS_COORDINATOR, _MockTrialsCoordinator)
    reg.register(AgentType.TRIAL_AGGREGATOR, TrialAggregatorAgent)
    reg.register(AgentType.CROSS_INDICATION_COORD, CrossIndicationCoordinator)
    reg.register(AgentType.REPORT_SYNTHESIZER, ReportSynthesizerAgent)

    factory = AgentFactory(reg, bus, **deps)
    reg.register(
        AgentType.RESEARCH_COORDINATOR,
        lambda **kw: ResearchCoordinatorAgent(**kw, factory=factory),
    )

    graph = build_graph(factory)
    state = PipelineState(run_id="test_run", raw_input="Stage III NSCLC, EGFR exon 19 deletion.")
    final = await graph.ainvoke(state)

    def _get(key):
        return final[key] if isinstance(final, dict) else getattr(final, key)

    assert _get("condition") == "NSCLC"
    assert DISCLAIMER in _get("final_report")
    assert _get("source_summaries")
