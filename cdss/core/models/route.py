from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    mode: str  # chat | research | clarify
    confidence: float = 0.0
    clarifying_question: str = ""
