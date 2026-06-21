import httpx

from cdss.core.models.trial import ClinicalTrial

_BASE = "https://clinicaltrials.gov/api/v2/studies"

EVIDENCE_LABELS = {1: "In-vitro", 2: "Animal", 3: "Phase I/II", 4: "Phase III adjacent"}


async def fetch_trials(
    condition: str,
    biomarker_genes: list[str],
    base_url: str = _BASE,
    max_results: int = 10,
) -> list[ClinicalTrial]:
    """Query ClinicalTrials.gov v2 for active/recruiting trials."""
    query_parts = [condition] + biomarker_genes
    params = {
        "query.cond": " ".join(query_parts),
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
        "pageSize": max_results,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
        studies = resp.json().get("studies", [])
        return [_parse(s) for s in studies if _parse(s) is not None]
    except Exception:
        return []  # graceful degradation per FR-005


def _parse(study: dict) -> ClinicalTrial | None:
    try:
        proto = study["protocolSection"]
        id_mod = proto["identificationModule"]
        status_mod = proto["statusModule"]
        desc_mod = proto.get("descriptionModule", {})
        design_mod = proto.get("designModule", {})

        locations = [
            loc.get("facility", {}).get("name", "")
            for loc in proto.get("contactsLocationsModule", {}).get("locations", [])[:3]
        ]
        nct_id = id_mod.get("nctId", "")
        return ClinicalTrial(
            nct_id=nct_id,
            title=id_mod.get("briefTitle", ""),
            phase=", ".join(design_mod.get("phases", ["N/A"])),
            status=status_mod.get("overallStatus", ""),
            locations=[l for l in locations if l],
            eligibility_summary=desc_mod.get("briefSummary", "")[:500],
            url=f"https://clinicaltrials.gov/study/{nct_id}",
        )
    except (KeyError, TypeError):
        return None
