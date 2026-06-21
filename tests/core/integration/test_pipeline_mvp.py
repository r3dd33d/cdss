"""MVP pipeline integration test with all external calls mocked."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cdss.agents.factory import AgentFactory
from cdss.agents.intake.intake_agent import IntakeAgent
from cdss.agents.registry import AgentRegistry
from cdss.agents.research.aggregator_agent import ResearchAggregatorAgent
from cdss.agents.research.coordinator_agent import ResearchCoordinatorAgent
from cdss.agents.research.source_reader_agent import SourceReaderAgent
from cdss.agents.synthesis.report_agent import ReportSynthesizerAgent
from cdss.agents.trials.trials_agent import TrialsAgent
from cdss.agents.cross_indication.coordinator_agent import CrossIndicationCoordinator
from cdss.core.enums import AgentType
from cdss.core.models.report import FinalReport
from cdss.knowledge.graph import loader
from cdss.llm.prompts.synthesizer import DISCLAIMER
from cdss.observability.event_bus import EventBus
from cdss.observability.trace_store import TraceStore
from cdss.pipeline.state import PipelineState
from cdss.pipeline.workflow import build_graph
from cdss.sources.registry import SourceRegistry, SearchConfig, FetchConfig, LLMConfig, SiteConfig


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
    reg.register(AgentType.REPORT_SYNTHESIZER, ReportSynthesizerAgent)
    reg.register(AgentType.TRIALS, lambda **kw: _MockTrialsAgent())
    reg.register(AgentType.CROSS_INDICATION_COORD, CrossIndicationCoordinator)

    factory = AgentFactory(reg, bus, **deps)
    reg.register(
        AgentType.RESEARCH_COORDINATOR,
        lambda **kw: ResearchCoordinatorAgent(**kw, factory=factory),
    )

    graph = build_graph(factory)
    state = PipelineState(run_id="test_run", raw_input="Stage III NSCLC, EGFR exon 19 deletion.")
    final = await graph.ainvoke(state)
    # LangGraph returns dict or Pydantic model depending on version.
    def _get(key):
        return final[key] if isinstance(final, dict) else getattr(final, key)

    assert _get("condition") == "NSCLC"
    assert DISCLAIMER in _get("final_report")
    assert _get("source_summaries")  # at least one source was read


from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.observability.run_context import RunContext

class _MockTrialsAgent(BaseAgent):
    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        return AgentResult(run_id=ctx.run_id, data=[])
