from time import monotonic

from pydantic import BaseModel

from cdss.agents.base import AgentTask, AgentResult, BaseAgent
from cdss.core.models.source import SourceRef, SourceSummary
from cdss.llm.client import LLMClient
from cdss.llm.prompts.source_reader import SOURCE_READER_PROMPT
from cdss.observability.run_context import RunContext
from cdss.sources.extract.html import extract_html
from cdss.sources.extract.pdf import extract_pdf
from cdss.sources.fetch.base import AbstractFetcher


class SourceReaderTask(AgentTask):
    source: SourceRef
    question: str
    condition: str
    stage: str
    max_tokens: int = 1024
    max_content_chars: int = 12000


class SourceReaderAgent(BaseAgent):
    def __init__(self, llm: LLMClient, fetcher: AbstractFetcher, **_) -> None:
        self._llm = llm
        self._fetcher = fetcher

    async def run(self, task: AgentTask, ctx: RunContext) -> AgentResult:
        t: SourceReaderTask = task  # type: ignore[assignment]
        start = monotonic()
        raw = await self._fetcher.fetch(t.source.url)
        # Choose extractor by content type heuristic.
        if t.source.url.lower().endswith(".pdf"):
            text = extract_pdf(raw, t.max_content_chars)
        else:
            text = extract_html(raw, t.max_content_chars)

        prompt = SOURCE_READER_PROMPT.format(
            condition=t.condition, stage=t.stage,
            question=t.question, page_text=text,
        )
        excerpt = self._llm.chat(prompt, max_tokens=t.max_tokens)
        duration = int((monotonic() - start) * 1000)

        summary = SourceSummary(
            source=t.source,
            relevant_excerpt=excerpt,
            confidence=min(1.0, len(excerpt) / 500),
            fetch_duration_ms=duration,
            agent_run_id=ctx.run_id,
        )
        return AgentResult(run_id=ctx.run_id, data=summary)
