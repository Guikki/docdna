from dataclasses import dataclass

from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)


@dataclass(frozen=True)
class EvidenceReport:
    evidences: list[DocumentEvidence]

    @property
    def total(self) -> int:
        return len(self.evidences)

    @property
    def critical(self) -> int:
        return self._count_by_severity(
            EvidenceSeverity.CRITICAL
        )

    @property
    def high(self) -> int:
        return self._count_by_severity(
            EvidenceSeverity.HIGH
        )

    @property
    def medium(self) -> int:
        return self._count_by_severity(
            EvidenceSeverity.MEDIUM
        )

    @property
    def low(self) -> int:
        return self._count_by_severity(
            EvidenceSeverity.LOW
        )

    @property
    def info(self) -> int:
        return self._count_by_severity(
            EvidenceSeverity.INFO
        )

    @property
    def has_evidences(self) -> bool:
        return bool(self.evidences)

    @property
    def highest_severity(
        self,
    ) -> EvidenceSeverity | None:
        severity_order = [
            EvidenceSeverity.CRITICAL,
            EvidenceSeverity.HIGH,
            EvidenceSeverity.MEDIUM,
            EvidenceSeverity.LOW,
            EvidenceSeverity.INFO,
        ]

        for severity in severity_order:
            if self._count_by_severity(severity):
                return severity

        return None

    def _count_by_severity(
        self,
        severity: EvidenceSeverity,
    ) -> int:
        return sum(
            evidence.severity == severity
            for evidence in self.evidences
        )