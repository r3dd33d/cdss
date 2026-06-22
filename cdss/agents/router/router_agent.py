import json

from cdss.agents.base import BaseAgent, AgentTask, AgentResult
from cdss.core.exceptions import LLMError
from cdss.core.models.route import RouteDecision
from cdss.llm.client import LLMClient
from cdss.llm.json_utils import strip_json_fences
from cdss.llm.prompts.router import ROUTER_PROMPT
from cdss.observability.run_context import RunContext


class RouterTask(AgentTask):
    text: str
    has_prior_report: bool = False
    max_tokens: int = 256


class RouterAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: RouterTask = task  # type: ignore[assignment]
        prompt = ROUTER_PROMPT.format(text=t.text, has_prior_report=t.has_prior_report)
        raw = self._llm.chat(prompt, max_tokens=t.max_tokens)
        try:
            data = json.loads(strip_json_fences(raw))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Router JSON parse failed: {exc}") from exc

        mode = data.get("mode", "clarify")
        if mode not in ("chat", "research", "clarify"):
            mode = "clarify"
        decision = RouteDecision(
            mode=mode,
            confidence=float(data.get("confidence", 0)),
            clarifying_question=data.get("clarifying_question", ""),
        )
        return AgentResult(run_id=ctx.run_id, data=decision)
