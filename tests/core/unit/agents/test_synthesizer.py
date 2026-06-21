import pytest
from unittest.mock import MagicMock

from cdss.agents.synthesis.report_agent import ReportSynthesizerAgent, SynthesizerTask
from cdss.core.models.patient import PatientProfile
from cdss.core.models.report import FinalReport
from cdss.llm.prompts.synthesizer import DISCLAIMER
from cdss.observability.run_context import RunContext


def _task() -> SynthesizerTask:
    return SynthesizerTask(
        profile=PatientProfile(condition="NSCLC", stage="III"),
        standard_care="Osimertinib is standard first-line.",
        source_summaries=[],
        trials=[],
        hypotheses=[],
        validation_flags=[],
    )


@pytest.mark.asyncio
async def test_report_contains_disclaimer():
    llm = MagicMock()
    llm.chat.return_value = "# Report\nSome content."
    agent = ReportSynthesizerAgent(llm=llm)
    result = await agent.run(_task(), RunContext(run_id="r1"))
    report: FinalReport = result.data
    assert DISCLAIMER in report.markdown


@pytest.mark.asyncio
async def test_report_includes_disclaimer_even_if_llm_omits_it():
    llm = MagicMock()
    llm.chat.return_value = "No disclaimer here at all."
    agent = ReportSynthesizerAgent(llm=llm)
    result = await agent.run(_task(), RunContext(run_id="r1"))
    assert DISCLAIMER in result.data.markdown


@pytest.mark.asyncio
async def test_report_profile_preserved():
    llm = MagicMock()
    llm.chat.return_value = f"Report.\n\n{DISCLAIMER}"
    agent = ReportSynthesizerAgent(llm=llm)
    result = await agent.run(_task(), RunContext(run_id="r1"))
    assert result.data.profile.condition == "NSCLC"
