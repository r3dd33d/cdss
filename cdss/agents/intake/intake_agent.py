import json

from pydantic import BaseModel

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.exceptions import LLMError
from cdss.core.models.patient import Biomarker, PatientProfile
from cdss.llm.client import LLMClient
from cdss.llm.json_utils import strip_json_fences
from cdss.llm.prompts.intake import INTAKE_PROMPT
from cdss.observability.run_context import RunContext


class IntakeTask(AgentTask):
    patient_text: str
    max_tokens: int = 1024


class IntakeAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: IntakeTask = task  # type: ignore[assignment]
        prompt = INTAKE_PROMPT.format(patient_text=t.patient_text)
        raw = self._llm.chat(prompt, max_tokens=t.max_tokens)
        try:
            data = json.loads(strip_json_fences(raw))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Intake JSON parse failed: {exc}") from exc

        profile = PatientProfile(
            condition=data.get("condition", ""),
            stage=data.get("stage", ""),
            biomarkers=[Biomarker(**b) for b in data.get("biomarkers", []) if b.get("gene")],
            current_medications=data.get("current_medications", []),
            prior_therapies=data.get("prior_therapies", []),
        )
        return AgentResult(run_id=ctx.run_id, data=profile)
