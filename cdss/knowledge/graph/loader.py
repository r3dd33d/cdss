"""Load PrimeKG from Harvard Dataverse into a NetworkX graph (lazy, cached)."""
import csv
import os
from pathlib import Path

import networkx as nx

KG: nx.MultiDiGraph = nx.MultiDiGraph()
KG_AVAILABLE: bool = False


def load_primekg(cache_dir: Path) -> bool:
    """Download and load PrimeKG; return True if successful."""
    global KG, KG_AVAILABLE
    nodes_path = cache_dir / "primekg_nodes.csv"
    edges_path = cache_dir / "primekg_edges.csv"

    if not (nodes_path.exists() and edges_path.exists()):
        try:
            _download(cache_dir, nodes_path, edges_path)
        except Exception as exc:
            print(f"PrimeKG unavailable: {exc}")
            KG_AVAILABLE = False
            return False

    KG = nx.MultiDiGraph()
    _load_nodes(nodes_path)
    _load_edges(edges_path)
    KG_AVAILABLE = True
    return True


def _download(cache_dir: Path, nodes_path: Path, edges_path: Path) -> None:
    import urllib.request
    cache_dir.mkdir(parents=True, exist_ok=True)
    doi = "doi:10.7910/DVN/IXA7BM"
    api = "https://dataverse.harvard.edu/api"
    import json
    import urllib.request as req
    with req.urlopen(f"{api}/datasets/:persistentId/?persistentId={doi}", timeout=30) as r:
        files = json.loads(r.read())["data"]["latestVersion"]["files"]

    def _pick(keywords):
        for f in files:
            name = f["dataFile"]["filename"].lower()
            if any(kw in name for kw in keywords):
                return f["dataFile"]["id"], f["dataFile"]["filename"]
        return None, None

    for fid, fname, dest in [
        (*_pick(["node"]), nodes_path),
        (*_pick(["edge", "kg_raw", "kg.csv", "relations"]), edges_path),
    ]:
        if fid and not dest.exists():
            url = f"{api}/access/datafile/{fid}"
            urllib.request.urlretrieve(url, dest)


def _load_nodes(path: Path) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        id_col = next((c for c in cols if "index" in c or c == "id"), cols[0])
        name_col = next((c for c in cols if "name" in c), cols[1] if len(cols) > 1 else cols[0])
        type_col = next((c for c in cols if "type" in c), None)
        for row in reader:
            KG.add_node(
                row[id_col],
                name=row.get(name_col, ""),
                type=row.get(type_col, "") if type_col else "",
            )


def _load_edges(path: Path) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        src = next((c for c in cols if c in ("x_index", "head_index", "source", "src")), cols[0])
        dst = next((c for c in cols if c in ("y_index", "tail_index", "target", "dst")), cols[1])
        rel = next((c for c in cols if "relation" in c or "type" in c), None)
        for row in reader:
            KG.add_edge(row[src], row[dst], relation=row.get(rel, "RELATED_TO") if rel else "RELATED_TO")
