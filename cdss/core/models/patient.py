from pydantic import BaseModel, Field


class Biomarker(BaseModel):
    gene: str
    variant_type: str
    details: str = ""


class PatientProfile(BaseModel):
    condition: str = ""
    stage: str = ""
    biomarkers: list[Biomarker] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    prior_therapies: list[str] = Field(default_factory=list)
