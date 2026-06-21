"""Integration: cross-indication skips gracefully when KG is unavailable."""
import pytest
import networkx as nx

from cdss.agents.cross_indication.coordinator_agent import CrossIndicationCoordinator, CrossIndicationTask
from cdss.core.models.patient import PatientProfile, Biomarker
from cdss.knowledge.graph import loader, queries
from cdss.observability.run_context import RunContext


def _task():
    return CrossIndicationTask(
        profile=PatientProfile(
            condition="NSCLC",
            biomarkers=[Biomarker(gene="EGFR", variant_type="exon 19 deletion")],
        )
    )


@pytest.mark.asyncio
async def test_skips_when_kg_unavailable(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)
    agent = CrossIndicationCoordinator()
    result = await agent.run(_task(), RunContext(run_id="r1"))
    assert result.data == []
    assert "KG_SKIPPED" in result.validation_flags


@pytest.mark.asyncio
async def test_returns_hypotheses_with_kg(monkeypatch):
    g = nx.MultiDiGraph()
    g.add_node("n1", name="EGFR", type="gene")
    g.add_node("n2", name="Erlotinib", type="drug")
    g.add_node("n3", name="CML", type="disease")
    g.add_edge("n1", "n2", relation="TARGETED_BY")
    g.add_edge("n2", "n3", relation="TREATS")
    monkeypatch.setattr(loader, "KG", g)
    monkeypatch.setattr(loader, "KG_AVAILABLE", True)

    agent = CrossIndicationCoordinator()
    result = await agent.run(_task(), RunContext(run_id="r1"))
    assert len(result.data) > 0
    assert result.data[0].drug_name == "Erlotinib"
