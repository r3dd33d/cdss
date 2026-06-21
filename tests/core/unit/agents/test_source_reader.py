import pytest
from unittest.mock import AsyncMock, MagicMock

from cdss.agents.research.source_reader_agent import SourceReaderAgent, SourceReaderTask
from cdss.core.exceptions import FetchError
from cdss.core.models.source import SourceRef, SourceSummary
from cdss.observability.run_context import RunContext


def _ref() -> SourceRef:
    return SourceRef(url="https://nccn.org/page", title="NCCN Guide", site_id="nccn", rank=1)


def _agent(fetch_result=b"<p>EGFR guidelines text</p>", llm_response="Osimertinib is first-line."):
    llm = MagicMock()
    llm.chat.return_value = llm_response
    fetcher = AsyncMock()
    fetcher.fetch.return_value = fetch_result
    return SourceReaderAgent(llm=llm, fetcher=fetcher)


@pytest.mark.asyncio
async def test_returns_source_summary():
    agent = _agent()
    task = SourceReaderTask(source=_ref(), question="standard care?", condition="NSCLC", stage="III")
    result = await agent.run(task, RunContext(run_id="r1"))
    assert isinstance(result.data, SourceSummary)
    assert "Osimertinib" in result.data.relevant_excerpt


@pytest.mark.asyncio
async def test_fetch_failure_propagates():
    llm = MagicMock()
    fetcher = AsyncMock()
    fetcher.fetch.side_effect = FetchError("timeout")
    agent = SourceReaderAgent(llm=llm, fetcher=fetcher)
    task = SourceReaderTask(source=_ref(), question="q", condition="NSCLC", stage="III")
    with pytest.raises(FetchError):
        await agent.run(task, RunContext(run_id="r1"))
