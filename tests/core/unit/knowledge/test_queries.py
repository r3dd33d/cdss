"""Unit tests for KG queries using a stub in-memory graph."""
import networkx as nx
import pytest

from cdss.knowledge.graph import loader, queries


def _build_stub_kg():
    """gene → pathway → drug triangle."""
    g = nx.MultiDiGraph()
    g.add_node("n1", name="EGFR", type="gene")
    g.add_node("n2", name="MAPK pathway", type="pathway")
    g.add_node("n3", name="Erlotinib", type="drug")
    g.add_node("n4", name="Lung adenocarcinoma", type="disease")
    g.add_edge("n1", "n2", relation="INVOLVED_IN")
    g.add_edge("n2", "n3", relation="TARGETED_BY")
    g.add_edge("n3", "n4", relation="TREATS")
    return g


@pytest.fixture(autouse=True)
def stub_kg(monkeypatch):
    monkeypatch.setattr(loader, "KG", _build_stub_kg())
    monkeypatch.setattr(loader, "KG_AVAILABLE", True)


def test_find_node_by_name():
    nid = queries.find_node_by_name("EGFR")
    assert nid == "n1"


def test_find_node_by_name_case_insensitive():
    assert queries.find_node_by_name("egfr") == "n1"


def test_find_node_unknown_returns_none():
    assert queries.find_node_by_name("BRAF_UNKNOWN") is None


def test_find_drugs_for_gene_returns_results():
    drugs = queries.find_drugs_for_gene("EGFR", max_hops=2)
    names = [d["drug"] for d in drugs]
    assert "Erlotinib" in names


def test_find_drugs_unavailable_returns_empty(monkeypatch):
    monkeypatch.setattr(loader, "KG_AVAILABLE", False)
    assert queries.find_drugs_for_gene("EGFR") == []


def test_find_drugs_unknown_gene_returns_empty():
    assert queries.find_drugs_for_gene("NONEXISTENT_GENE_XYZ") == []
