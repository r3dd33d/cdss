from pydantic import BaseModel


class OffLabelHypothesis(BaseModel):
    drug_name: str
    approved_indication: str
    shared_mechanism: str
    # 1=in-vitro, 2=animal, 3=Phase I/II, 4=Phase III adjacent
    evidence_level: int
    evidence_label: str
    citation: str
