import logging

from curl_cffi.requests import AsyncSession

from cdss.core.models.patient import PatientProfile
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


async def fetch_study(nct_id: str, base_url: str = _BASE) -> dict | None:
    """Fetch a single study record by NCT id."""
    try:
        async with AsyncSession() as client:
            resp = await client.get(
                f"{base_url}/{nct_id}",
                params={"format": "json"},
                impersonate="chrome",
                timeout=20,
            )
            resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("fetch_study failed for %s: %s", nct_id, exc)
        return None


def study_text(study: dict, *, max_chars: int = 12000) -> str:
    """Extract eligibility and intervention text for LLM summarization."""
    proto = study.get("protocolSection", study)
    parts: list[str] = []
    id_mod = proto.get("identificationModule", {})
    parts.append(f"NCT: {id_mod.get('nctId', '')}\nTitle: {id_mod.get('briefTitle', '')}")

    desc = proto.get("descriptionModule", {})
    if desc.get("briefSummary"):
        parts.append(f"BRIEF SUMMARY:\n{desc['briefSummary']}")
    if desc.get("detailedDescription"):
        parts.append(f"DETAILED DESCRIPTION:\n{desc['detailedDescription'][:4000]}")

    elig = proto.get("eligibilityModule", {})
    if elig.get("eligibilityCriteria"):
        parts.append(f"ELIGIBILITY CRITERIA:\n{elig['eligibilityCriteria'][:6000]}")

    arms = proto.get("armsInterventionsModule", {})
    interventions = arms.get("interventions", [])
    if interventions:
        lines = [f"- {i.get('name', '')}: {i.get('description', '')}" for i in interventions]
        parts.append("INTERVENTIONS:\n" + "\n".join(lines))

    text = "\n\n".join(parts)
    return text[:max_chars]


def rank_trials(
    trials: list[ClinicalTrial],
    profile: PatientProfile,
    *,
    limit: int = 5,
    recruiting_boost: int = 2,
) -> list[ClinicalTrial]:
    """Heuristic rank: recruiting status, phase, biomarker/condition overlap."""
    genes = [b.gene.upper() for b in profile.biomarkers if b.gene]
    cond_tokens = {t for t in profile.condition.lower().split() if len(t) > 3}

    def score(trial: ClinicalTrial) -> int:
        s = 0
        if trial.status == "RECRUITING":
            s += recruiting_boost
        phase_upper = trial.phase.upper()
        if "PHASE3" in phase_upper:
            s += 2
        elif "PHASE2" in phase_upper:
            s += 1
        blob = (trial.title + " " + " ".join(trial.keywords)).upper()
        for gene in genes:
            if gene in blob:
                s += 2
        title_lower = trial.title.lower()
        if any(tok in title_lower for tok in cond_tokens):
            s += 1
        return s

    ranked = sorted(trials, key=score, reverse=True)
    return ranked[:limit]


def _parse(study: dict) -> ClinicalTrial | None:
    try:
        proto = study["protocolSection"]
        id_mod = proto["identificationModule"]
        status_mod = proto["statusModule"]
        desc_mod = proto.get("descriptionModule", {})
        design_mod = proto.get("designModule", {})
        cond_mod = proto.get("conditionsModule", {})
        keywords = list(cond_mod.get("keywords") or [])

        locations = [
            _facility_name(loc)
            for loc in proto.get("contactsLocationsModule", {}).get("locations", [])[:3]
        ]
        nct_id = id_mod.get("nctId", "")
        return ClinicalTrial(
            nct_id=nct_id,
            title=id_mod.get("briefTitle", ""),
            phase=", ".join(design_mod.get("phases", ["N/A"])),
            status=status_mod.get("overallStatus", ""),
            locations=[loc for loc in locations if loc],
            eligibility_summary=desc_mod.get("briefSummary", "")[:500],
            url=f"https://clinicaltrials.gov/study/{nct_id}",
            keywords=keywords,
        )
    except (KeyError, TypeError, AttributeError):
        return None


def _facility_name(loc: dict) -> str:
    facility = loc.get("facility", "")
    if isinstance(facility, dict):
        return facility.get("name", "")
    return str(facility) if facility else ""
