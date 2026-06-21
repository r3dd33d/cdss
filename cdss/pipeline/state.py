from pydantic import BaseModel, Field

from cdss.core.models.patient import PatientProfile, Biomarker
from cdss.core.models.source import SourceSummary
from cdss.core.models.trial import ClinicalTrial
from cdss.core.models.hypothesis import OffLabelHypothesis


class PipelineState(BaseModel):
    run_id: str
    raw_input: str
    input_is_pdf: bool = False

    # Populated by IntakeAgent
    condition: str = ""
    stage: str = ""
    biomarkers: list[Biomarker] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    prior_therapies: list[str] = Field(default_factory=list)

    # Populated by research phase
    source_summaries: list[SourceSummary] = Field(default_factory=list)
    standard_care_summary: str = ""

    # Populated by TrialsAgent
    clinical_trials: list[ClinicalTrial] = Field(default_factory=list)

    # Populated by CrossIndicationCoordinator
    off_label_hypotheses: list[OffLabelHypothesis] = Field(default_factory=list)

    # Populated by ReportSynthesizer
    validation_flags: list[str] = Field(default_factory=list)
    final_report: str = ""

    # Retry control (mirrors notebook behavior)
    retry_count: int = 0
    max_retries: int = 2

    def _profile(self) -> "PatientProfile":
        from cdss.core.models.patient import PatientProfile
        return PatientProfile(
            condition=self.condition,
            stage=self.stage,
            biomarkers=self.biomarkers,
            current_medications=self.current_medications,
            prior_therapies=self.prior_therapies,
        )
