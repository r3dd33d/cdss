"""BFS traversal from a gene node to drug candidates via shared pathways."""
from cdss.knowledge.graph import loader

_DRUG_TYPES = {"drug", "small molecule", "compound"}
_DISEASE_TYPES = {"disease", "phenotype", "indication"}


def find_node_by_name(name: str) -> str | None:
    name_lower = name.lower()
    for nid, attrs in loader.KG.nodes(data=True):
        if name_lower in attrs.get("name", "").lower():
            return nid
    return None


def find_drugs_for_gene(gene: str, max_hops: int = 2, limit: int = 15) -> list[dict]:
    """BFS from gene to drug candidates; returns list of {drug, approved_indication, shared_pathway}."""
    if not loader.KG_AVAILABLE:
        return []
    gene_node = find_node_by_name(gene)
    if not gene_node:
        return []

    visited = {gene_node}
    frontier = {gene_node}
    for _ in range(max_hops):
        next_f = set()
        for n in frontier:
            next_f.update(loader.KG.successors(n))
            next_f.update(loader.KG.predecessors(n))
        frontier = next_f - visited
        visited.update(frontier)

    results, seen = [], set()
    for nid in visited:
        attrs = loader.KG.nodes[nid]
        if attrs.get("type", "").lower() not in _DRUG_TYPES:
            continue
        drug_name = attrs.get("name", "")
        if not drug_name or drug_name in seen:
            continue
        seen.add(drug_name)
        indications = [
            loader.KG.nodes[nb].get("name", "")
            for nb in list(loader.KG.successors(nid)) + list(loader.KG.predecessors(nid))
            if loader.KG.nodes[nb].get("type", "").lower() in _DISEASE_TYPES
        ]
        results.append({
            "drug": drug_name,
            "approved_indication": ", ".join(indications[:2]) or "see literature",
            "shared_pathway": f"connected via {max_hops}-hop path from {gene}",
        })
        if len(results) >= limit:
            break
    return results
