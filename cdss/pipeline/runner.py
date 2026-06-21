"""Core pipeline entry point; UI-agnostic."""
import uuid

from cdss.agents.factory import AgentFactory
from cdss.agents.intake.intake_agent import IntakeAgent
from cdss.agents.registry import AgentRegistry
from cdss.agents.research.aggregator_agent import ResearchAggregatorAgent
from cdss.agents.research.coordinator_agent import ResearchCoordinatorAgent
from cdss.agents.research.source_reader_agent import SourceReaderAgent
from cdss.agents.synthesis.report_agent import ReportSynthesizerAgent
from cdss.config.settings import Settings
from cdss.core.enums import AgentType, EventType
from cdss.core.models.report import FinalReport
from cdss.llm.client import LLMClient
from cdss.observability.event_bus import EventBus
from cdss.observability.events import AgentEvent
from cdss.observability.trace_store import TraceStore
from cdss.pipeline.state import PipelineState
from cdss.pipeline.workflow import build_graph
from cdss.sources.fetch.httpx_fetcher import HttpxFetcher
from cdss.sources.registry import load_registry
from cdss.sources.search.site_scoped import SerperSiteScoped


class Runner:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._src_registry = load_registry(settings.sources_yaml)
        llm_cfg = self._src_registry.llm
        self._llm = LLMClient(settings.groq_api_key, llm_cfg.model_preference)
        self._fetcher = HttpxFetcher(
            self._src_registry.fetch.timeout_seconds,
            self._src_registry.fetch.user_agent,
        )
        enabled_sites = [s.domain for s in self._src_registry.enabled_sites]
        self._search = SerperSiteScoped(
            settings.serper_api_key, enabled_sites, self._src_registry.fetch.user_agent
        )
        self.trace_store = TraceStore()
        self.bus = EventBus(self.trace_store)

    def _make_factory(self) -> AgentFactory:
        reg = AgentRegistry()
        deps = dict(
            llm=self._llm,
            fetcher=self._fetcher,
            search=self._search,
            source_registry=self._src_registry,
        )
        reg.register(AgentType.INTAKE, IntakeAgent)
        reg.register(AgentType.SOURCE_READER, SourceReaderAgent)
        reg.register(AgentType.RESEARCH_AGGREGATOR, ResearchAggregatorAgent)
        reg.register(AgentType.REPORT_SYNTHESIZER, ReportSynthesizerAgent)
        factory = AgentFactory(reg, self.bus, **deps)

        # Give coordinator access to the factory for spawning readers.
        reg.register(AgentType.RESEARCH_COORDINATOR,
                     lambda **kw: ResearchCoordinatorAgent(**kw, factory=factory))
        return factory

    async def run(self, raw_input: str, *, is_pdf: bool = False) -> FinalReport:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        factory = self._make_factory()
        graph = build_graph(factory)

        self.bus.publish(AgentEvent.build(EventType.RUN_STARTED, run_id))
        state = PipelineState(run_id=run_id, raw_input=raw_input, input_is_pdf=is_pdf)

        try:
            final_state: PipelineState = await graph.ainvoke(state)
            from cdss.llm.prompts.synthesizer import DISCLAIMER
            from cdss.core.models.patient import PatientProfile
            report = FinalReport(
                markdown=final_state.final_report,
                profile=final_state._profile(),
                sources=[s.source for s in final_state.source_summaries],
                trials_count=len(final_state.clinical_trials),
                hypotheses_count=len(final_state.off_label_hypotheses),
                validation_flags=final_state.validation_flags,
            )
            self.bus.publish(AgentEvent.build(EventType.RUN_COMPLETED, run_id))
            return report
        except Exception as exc:
            self.bus.publish(AgentEvent.build(EventType.RUN_FAILED, run_id, error=str(exc)))
            raise
        finally:
            self.bus.close(run_id)


def build_runner(settings: Settings) -> Runner:
    return Runner(settings)
