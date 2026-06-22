import logging

from curl_cffi.requests import AsyncSession

from cdss.core.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)

_BASE = "https://clinicaltrials.gov/api/v2/studies"

EVIDENCE_LABELS = {1: "In-vitro", 2: "Animal", 3: "Phase I/II", 4: "Phase III adjacent"}


async def fetch_trials(
    condition: str,
    biomarker_genes: list[str],
    base_url: str = _BASE,
    max_results: int = 10,
) -> tuple[list[ClinicalTrial], str | None]:
    """Query ClinicalTrials.gov v2 for active/recruiting trials."""
    if not condition.strip():
        return [], "Trials skipped: no condition extracted from intake."

    query_parts = [condition] + biomarker_genes
    params = {
        "query.cond": " ".join(query_parts),
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
        "pageSize": max_results,
        "format": "json",
    }
    try:
        # httpx/requests get 403 from ClinicalTrials.gov CDN (TLS fingerprinting).
        async with AsyncSession() as client:
            resp = await client.get(
                base_url,
                params=params,
                impersonate="chrome",
                timeout=20,
            )
            resp.raise_for_status()
        studies = resp.json().get("studies", [])
        trials = [t for s in studies if (t := _parse(s)) is not None]
        return trials, None
    except Exception as exc:
        logger.warning("ClinicalTrials.gov fetch failed: %s", exc)
        return [], f"Trials API error: {exc}"


def _parse(study: dict) -> ClinicalTrial | None:
    try:
        proto = study["protocolSection"]
        id_mod = proto["identificationModule"]
        status_mod = proto["statusModule"]
        desc_mod = proto.get("descriptionModule", {})
        design_mod = proto.get("designModule", {})

        locations = [_facility_name(loc) for loc in proto.get("contactsLocationsModule", {}).get("locations", [])[:3]]
        nct_id = id_mod.get("nctId", "")
        return ClinicalTrial(
            nct_id=nct_id,
            title=id_mod.get("briefTitle", ""),
            phase=", ".join(design_mod.get("phases", ["N/A"])),
            status=status_mod.get("overallStatus", ""),
            locations=[loc for loc in locations if loc],
            eligibility_summary=desc_mod.get("briefSummary", "")[:500],
            url=f"https://clinicaltrials.gov/study/{nct_id}",
        )
    except (KeyError, TypeError, AttributeError):
        return None


def _facility_name(loc: dict) -> str:
    facility = loc.get("facility", "")
    if isinstance(facility, dict):
        return facility.get("name", "")
    return str(facility) if facility else ""
