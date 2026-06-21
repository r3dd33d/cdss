from pydantic import BaseModel, Field

from cdss.core.models.patient import PatientProfile
from cdss.core.models.source import SourceRef


class FinalReport(BaseModel):
    markdown: str
    profile: PatientProfile
    sources: list[SourceRef] = Field(default_factory=list)
    trials_count: int = 0
    hypotheses_count: int = 0
    validation_flags: list[str] = Field(default_factory=list)
