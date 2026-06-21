"""Thin LangGraph node wrappers that call agents via the factory."""
from cdss.agents.intake.intake_agent import IntakeTask
from cdss.agents.research.aggregator_agent import AggregatorTask
from cdss.agents.research.coordinator_agent import CoordinatorTask
from cdss.agents.synthesis.report_agent import SynthesizerTask
from cdss.core.enums import AgentType
from cdss.pipeline.state import PipelineState


async def node_intake(state: PipelineState, *, factory) -> dict:
    task = IntakeTask(patient_text=state.raw_input)
    result = await factory.spawn(AgentType.INTAKE, task, parent_run_id=state.run_id)
    profile = result.data
    return dict(
        condition=profile.condition,
        stage=profile.stage,
        biomarkers=profile.biomarkers,
        current_medications=profile.current_medications,
        prior_therapies=profile.prior_therapies,
    )


async def node_research(state: PipelineState, *, factory) -> dict:
    task = CoordinatorTask(
        question=f"Standard care for {state.condition} {state.stage}",
        condition=state.condition,
        stage=state.stage,
    )
    result = await factory.spawn(AgentType.RESEARCH_COORDINATOR, task, parent_run_id=state.run_id)
    summaries = result.data

    agg_task = AggregatorTask(
        summaries=summaries, condition=state.condition, stage=state.stage
    )
    agg_result = await factory.spawn(
        AgentType.RESEARCH_AGGREGATOR, agg_task, parent_run_id=state.run_id
    )
    return dict(source_summaries=summaries, standard_care_summary=agg_result.data)


async def node_synthesize(state: PipelineState, *, factory) -> dict:
    task = SynthesizerTask(
        profile=state._profile(),
        standard_care=state.standard_care_summary,
        source_summaries=state.source_summaries,
        trials=state.clinical_trials,
        hypotheses=state.off_label_hypotheses,
        validation_flags=state.validation_flags,
    )
    result = await factory.spawn(AgentType.REPORT_SYNTHESIZER, task, parent_run_id=state.run_id)
    report = result.data
    return dict(final_report=report.markdown, validation_flags=report.validation_flags)
