"""LangGraph workflow definition."""
import functools

from langgraph.graph import StateGraph, END

from cdss.pipeline.nodes import (
    node_cross_indication, node_intake, node_research, node_synthesize, node_trials_read,
)
from cdss.pipeline.state import PipelineState


def _should_retry(state: PipelineState) -> str:
    critical = [f for f in state.validation_flags if "error" in f.lower()]
    if critical and state.retry_count < state.max_retries:
        return "retry"
    return "done"


def build_graph(factory) -> StateGraph:
    """Build and compile the LangGraph pipeline, injecting the factory."""
    _intake = functools.partial(node_intake, factory=factory)
    _research = functools.partial(node_research, factory=factory)
    _trials = functools.partial(node_trials_read, factory=factory)
    _cross = functools.partial(node_cross_indication, factory=factory)
    _synthesize = functools.partial(node_synthesize, factory=factory)

    g = StateGraph(PipelineState)
    g.add_node("intake", _intake)
    g.add_node("research", _research)
    g.add_node("trials_read", _trials)
    g.add_node("cross_indication", _cross)
    g.add_node("synthesize", _synthesize)

    g.set_entry_point("intake")
    g.add_edge("intake", "research")
    g.add_edge("research", "trials_read")
    g.add_edge("trials_read", "cross_indication")
    g.add_edge("cross_indication", "synthesize")
    g.add_conditional_edges(
        "synthesize",
        _should_retry,
        {"retry": "intake", "done": END},
    )
    return g.compile()
