"""Sync bridge from Streamlit to async router/chat agents."""
from __future__ import annotations

import asyncio

from cdss.agents.chat.chat_agent import ChatAgent, ChatTask
from cdss.agents.router.router_agent import RouterAgent, RouterTask
from cdss.config.settings import load_settings
from cdss.core.models.report import FinalReport
from cdss.core.models.route import RouteDecision
from cdss.llm.client import LLMClient
from cdss.observability.run_context import RunContext
from cdss.sources.registry import load_registry


def _llm() -> LLMClient:
    settings = load_settings()
    reg = load_registry(settings.sources_yaml)
    return LLMClient(settings.groq_api_key, reg.llm.model_preference)


async def _route(text: str, *, has_prior_report: bool) -> RouteDecision:
    agent = RouterAgent(llm=_llm())
    result = await agent.run(
        RouterTask(text=text, has_prior_report=has_prior_report),
        RunContext(run_id="route_local"),
    )
    return result.data


async def _chat(text: str, *, prior_report: FinalReport | None) -> str:
    agent = ChatAgent(llm=_llm())
    result = await agent.run(
        ChatTask(text=text, prior_report=prior_report),
        RunContext(run_id="chat_local"),
    )
    return result.data


def route_message_sync(text: str, *, has_prior_report: bool = False) -> RouteDecision:
    return asyncio.run(_route(text, has_prior_report=has_prior_report))


def chat_reply_sync(text: str, *, prior_report: FinalReport | None = None) -> str:
    return asyncio.run(_chat(text, prior_report=prior_report))


def route_and_reply(
    text: str,
    *,
    has_prior_report: bool = False,
    prior_report: FinalReport | None = None,
) -> tuple[RouteDecision, str | None]:
    """Route then optionally chat; returns (decision, assistant_text or None)."""
    decision = route_message_sync(text, has_prior_report=has_prior_report)
    if decision.mode == "chat":
        return decision, chat_reply_sync(text, prior_report=prior_report)
    if decision.mode == "clarify":
        q = decision.clarifying_question or "Could you describe your diagnosis or what you'd like to research?"
        return decision, q
    return decision, None
