from cdss.core.models.patient import PatientProfile, Biomarker
from cdss.core.models.trial import ClinicalTrial
from cdss.integrations.clinical_trials import rank_trials


def _trial(nct: str, title: str, status: str, phase: str, keywords: list[str] | None = None):
    return ClinicalTrial(
        nct_id=nct,
        title=title,
        phase=phase,
        status=status,
        eligibility_summary="",
        url=f"https://clinicaltrials.gov/study/{nct}",
        keywords=keywords or [],
    )


def test_rank_prefers_recruiting_phase3_with_biomarker():
    profile = PatientProfile(
        condition="breast cancer",
        stage="IV",
        biomarkers=[Biomarker(gene="HER2", variant_type="Amplification", details="")],
    )
    trials = [
        _trial("NCT001", "Generic chemo study", "ACTIVE_NOT_RECRUITING", "PHASE1"),
        _trial("NCT002", "HER2 positive breast cancer trial", "RECRUITING", "PHASE3", ["HER2"]),
        _trial("NCT003", "Another breast cancer study", "RECRUITING", "PHASE2"),
    ]
    ranked = rank_trials(trials, profile, limit=2, recruiting_boost=2)
    assert ranked[0].nct_id == "NCT002"
    assert len(ranked) == 2


def test_rank_limit():
    profile = PatientProfile(condition="NSCLC", stage="III")
    trials = [_trial(f"NCT{i}", f"Trial {i}", "RECRUITING", "PHASE2") for i in range(10)]
    ranked = rank_trials(trials, profile, limit=5)
    assert len(ranked) == 5
