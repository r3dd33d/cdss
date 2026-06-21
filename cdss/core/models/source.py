from pydantic import BaseModel


class SourceRef(BaseModel):
    url: str
    title: str
    site_id: str
    rank: int


class SourceSummary(BaseModel):
    source: SourceRef
    relevant_excerpt: str
    confidence: float = 0.0
    fetch_duration_ms: int = 0
    agent_run_id: str = ""
