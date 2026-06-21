import pytest
from cdss.core.models.patient import Biomarker, PatientProfile
from cdss.core.models.source import SourceRef, SourceSummary
from cdss.core.models.trial import ClinicalTrial
from cdss.core.models.hypothesis import OffLabelHypothesis
from cdss.core.models.report import FinalReport


def test_patient_profile_defaults():
    p = PatientProfile()
    assert p.condition == ""
    assert p.biomarkers == []


def test_biomarker_round_trip():
    b = Biomarker(gene="EGFR", variant_type="exon 19 deletion", details="")
    assert Biomarker.model_validate(b.model_dump()).gene == "EGFR"


def test_source_ref_required_fields():
    with pytest.raises(Exception):
        SourceRef()  # missing required fields


def test_source_summary_defaults():
    ref = SourceRef(url="https://nccn.org/x", title="T", site_id="nccn", rank=1)
    s = SourceSummary(source=ref, relevant_excerpt="some text")
    assert s.confidence == 0.0


def test_clinical_trial_round_trip():
    t = ClinicalTrial(
        nct_id="NCT001",
        title="Trial",
        phase="III",
        status="RECRUITING",
        eligibility_summary="Adults with NSCLC",
        url="https://clinicaltrials.gov/study/NCT001",
    )
    assert t.nct_id == "NCT001"


def test_off_label_hypothesis():
    h = OffLabelHypothesis(
        drug_name="Imatinib",
        approved_indication="CML",
        shared_mechanism="BCR-ABL pathway",
        evidence_level=2,
        evidence_label="Animal",
        citation="doi:10.1/x",
    )
    assert h.evidence_level == 2


def test_final_report_includes_disclaimer():
    from cdss.core.models.patient import PatientProfile
    r = FinalReport(
        markdown="**Disclaimer**: not medical advice",
        profile=PatientProfile(condition="NSCLC"),
    )
    assert "Disclaimer" in r.markdown
