from pydantic import BaseModel, Field


class ClinicalTrial(BaseModel):
    nct_id: str
    title: str
    phase: str
    status: str
    locations: list[str] = Field(default_factory=list)
    eligibility_summary: str
    url: str
    keywords: list[str] = Field(default_factory=list)


class TrialSummary(BaseModel):
    nct_id: str
    title: str
    phase: str
    status: str
    url: str
    relevant_excerpt: str
    patient_fit_notes: str = ""
    confidence: float = 0.5
    agent_run_id: str = ""
