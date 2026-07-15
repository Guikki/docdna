from typing import Any

from pydantic import BaseModel


class CrossValidationFindingResponse(BaseModel):
    code: str
    title: str
    description: str
    severity: str
    confidence: float
    comparator: str
    document_ids: list[str]
    metadata: dict[str, Any]


class CrossValidationResultResponse(BaseModel):
    total_findings: int
    has_findings: bool
    findings: list[CrossValidationFindingResponse]