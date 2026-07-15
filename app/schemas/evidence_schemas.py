from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    code: str
    title: str
    description: str
    severity: str
    detector: str
    confidence: float