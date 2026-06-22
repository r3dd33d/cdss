import json
import pytest
from unittest.mock import MagicMock

from cdss.agents.router.router_agent import RouterAgent, RouterTask
from cdss.observability.run_context import RunContext


@pytest.mark.asyncio
async def test_router_classifies_chat():
    llm = MagicMock()
    llm.chat.return_value = json.dumps({
        "mode": "chat", "confidence": 0.9, "clarifying_question": "",
    })
    agent = RouterAgent(llm=llm)
    result = await agent.run(
        RouterTask(text="What is HER2?"),
        RunContext(run_id="r1"),
    )
    assert result.data.mode == "chat"


@pytest.mark.asyncio
async def test_router_classifies_research():
    llm = MagicMock()
    llm.chat.return_value = json.dumps({
        "mode": "research", "confidence": 0.85, "clarifying_question": "",
    })
    agent = RouterAgent(llm=llm)
    result = await agent.run(
        RouterTask(text="Stage III HER2+ breast cancer, looking for trials"),
        RunContext(run_id="r1"),
    )
    assert result.data.mode == "research"


@pytest.mark.asyncio
async def test_router_clarify_mode():
    llm = MagicMock()
    llm.chat.return_value = json.dumps({
        "mode": "clarify",
        "confidence": 0.4,
        "clarifying_question": "What is your diagnosis?",
    })
    agent = RouterAgent(llm=llm)
    result = await agent.run(RouterTask(text="help"), RunContext(run_id="r1"))
    assert result.data.mode == "clarify"
    assert "diagnosis" in result.data.clarifying_question.lower()
