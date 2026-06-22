from cdss.agents.base import BaseAgent, AgentTask, AgentResult
from cdss.core.models.report import FinalReport
from cdss.llm.client import LLMClient
from cdss.llm.prompts.chat import CHAT_PROMPT, CHAT_SYSTEM
from cdss.llm.prompts.synthesizer import DISCLAIMER
from cdss.observability.run_context import RunContext


class ChatTask(AgentTask):
    text: str
    prior_report: FinalReport | None = None
    max_tokens: int = 512


class ChatAgent(BaseAgent):
    def __init__(self, llm: LLMClient, **_) -> None:
        self._llm = llm

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: ChatTask = task  # type: ignore[assignment]
        prior = ""
        if t.prior_report:
            prior = t.prior_report.markdown[:2000]
        system = CHAT_SYSTEM.format(disclaimer=DISCLAIMER)
        prompt = CHAT_PROMPT.format(system=system, prior_context=prior or "None", text=t.text)
        reply = self._llm.chat(prompt, max_tokens=t.max_tokens)
        if DISCLAIMER not in reply:
            reply = f"{reply}\n\n{DISCLAIMER}"
        return AgentResult(run_id=ctx.run_id, data=reply)
