from pydantic import BaseModel, Field


class ClinicalTrial(BaseModel):
    nct_id: str
    title: str
    phase: str
    status: str
    locations: list[str] = Field(default_factory=list)
    eligibility_summary: str
    url: str
