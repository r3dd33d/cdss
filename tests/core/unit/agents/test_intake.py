import json
from unittest.mock import MagicMock

import pytest

from cdss.agents.intake.intake_agent import IntakeAgent, IntakeTask
from cdss.core.models.patient import PatientProfile
from cdss.observability.run_context import RunContext


def _agent(response: str) -> IntakeAgent:
    llm = MagicMock()
    llm.chat.return_value = response
    return IntakeAgent(llm=llm)


def _ctx() -> RunContext:
    return RunContext(run_id="test_run")


@pytest.mark.asyncio
async def test_parses_condition_and_stage():
    payload = json.dumps({
        "condition": "NSCLC",
        "stage": "III",
        "biomarkers": [{"gene": "EGFR", "variant_type": "exon 19 deletion", "details": ""}],
        "current_medications": ["osimertinib"],
        "prior_therapies": [],
    })
    agent = _agent(payload)
    result = await agent.run(IntakeTask(patient_text="..."), _ctx())
    profile: PatientProfile = result.data
    assert profile.condition == "NSCLC"
    assert profile.stage == "III"
    assert profile.biomarkers[0].gene == "EGFR"


@pytest.mark.asyncio
async def test_vague_input_returns_empty_profile():
    payload = json.dumps({
        "condition": "", "stage": "", "biomarkers": [],
        "current_medications": [], "prior_therapies": [],
    })
    agent = _agent(payload)
    result = await agent.run(IntakeTask(patient_text="I feel unwell"), _ctx())
    profile: PatientProfile = result.data
    assert profile.condition == ""


@pytest.mark.asyncio
async def test_strips_json_fences():
    payload = '```json\n{"condition":"NSCLC","stage":"II","biomarkers":[],"current_medications":[],"prior_therapies":[]}\n```'
    agent = _agent(payload)
    result = await agent.run(IntakeTask(patient_text="..."), _ctx())
    assert result.data.condition == "NSCLC"
