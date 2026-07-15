from dataclasses import dataclass

from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)


@dataclass(frozen=True)
class CrossValidationResult:
    findings: list[CrossValidationFinding]

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)