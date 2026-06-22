"""Thin LangGraph node wrappers that call agents via the factory."""
from cdss.agents.intake.intake_agent import IntakeTask
from cdss.agents.research.aggregator_agent import AggregatorTask
from cdss.agents.research.coordinator_agent import CoordinatorTask
from cdss.agents.synthesis.report_agent import SynthesizerTask
from cdss.agents.cross_indication.coordinator_agent import CrossIndicationTask
from cdss.agents.trials.coordinator_agent import TrialsCoordinatorTask
from cdss.agents.trials.aggregator_agent import TrialAggregatorTask
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


async def node_trials_read(state: PipelineState, *, factory) -> dict:
    if not state.condition.strip():
        flag = "Trials skipped: no condition extracted from intake."
        return dict(
            clinical_trials=[],
            trial_summaries=[],
            trials_matched_count=0,
            trials_aggregated="",
            validation_flags=list(state.validation_flags) + [flag],
        )

    task = TrialsCoordinatorTask(profile=state._profile())
    coord_result = await factory.spawn(
        AgentType.TRIALS_COORDINATOR, task, parent_run_id=state.run_id
    )
    data = coord_result.data
    flags = list(state.validation_flags) + coord_result.validation_flags

    agg_task = TrialAggregatorTask(
        summaries=data.trial_summaries,
        matched_count=data.trials_matched_count,
        condition=state.condition,
        stage=state.stage,
    )
    agg_result = await factory.spawn(
        AgentType.TRIAL_AGGREGATOR, agg_task, parent_run_id=state.run_id
    )
    return dict(
        clinical_trials=data.clinical_trials,
        trial_summaries=data.trial_summaries,
        trials_matched_count=data.trials_matched_count,
        trials_aggregated=agg_result.data,
        validation_flags=flags,
    )


async def node_cross_indication(state: PipelineState, *, factory) -> dict:
    task = CrossIndicationTask(profile=state._profile())
    result = await factory.spawn(
        AgentType.CROSS_INDICATION_COORD, task, parent_run_id=state.run_id
    )
    flags = list(state.validation_flags) + result.validation_flags
    return dict(off_label_hypotheses=result.data, validation_flags=flags)


async def node_synthesize(state: PipelineState, *, factory) -> dict:
    task = SynthesizerTask(
        profile=state._profile(),
        standard_care=state.standard_care_summary,
        source_summaries=state.source_summaries,
        trials_aggregated=state.trials_aggregated,
        trials_matched_count=state.trials_matched_count,
        trials_analyzed_count=len(state.trial_summaries),
        hypotheses=state.off_label_hypotheses,
        validation_flags=state.validation_flags,
    )
    result = await factory.spawn(AgentType.REPORT_SYNTHESIZER, task, parent_run_id=state.run_id)
    report = result.data
    return dict(final_report=report.markdown, validation_flags=report.validation_flags)
