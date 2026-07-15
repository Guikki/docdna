from app.domain.models.cross_validation_finding import (
    CrossValidationSeverity,
)
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)
from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.models.evidence_report import EvidenceReport


class EvidenceReportBuilder:

    def build(
        self,
        cross_validation_result: CrossValidationResult,
    ) -> EvidenceReport:
        evidences = [
            self._build_evidence(finding)
            for finding in cross_validation_result.findings
        ]

        evidences.sort(
            key=self._build_sort_key
        )

        return EvidenceReport(
            evidences=evidences
        )

    def _build_evidence(
        self,
        finding,
    ) -> DocumentEvidence:
        return DocumentEvidence(
            code=finding.code,
            title=finding.title,
            description=finding.description,
            severity=self._translate_severity(
                finding.severity
            ),
            confidence=self._normalize_confidence(
                finding.confidence
            ),
            source=finding.comparator,
            document_ids=list(
                finding.document_ids
            ),
            metadata=dict(
                finding.metadata
            ),
        )

    def _translate_severity(
        self,
        severity: CrossValidationSeverity,
    ) -> EvidenceSeverity:
        severity_map = {
            CrossValidationSeverity.INFO:
                EvidenceSeverity.INFO,
            CrossValidationSeverity.LOW:
                EvidenceSeverity.LOW,
            CrossValidationSeverity.MEDIUM:
                EvidenceSeverity.MEDIUM,
            CrossValidationSeverity.HIGH:
                EvidenceSeverity.HIGH,
            CrossValidationSeverity.CRITICAL:
                EvidenceSeverity.CRITICAL,
        }

        return severity_map.get(
            severity,
            EvidenceSeverity.INFO,
        )

    def _normalize_confidence(
        self,
        confidence: float,
    ) -> float:
        return round(
            min(
                max(float(confidence), 0.0),
                1.0,
            ),
            4,
        )

    def _build_sort_key(
        self,
        evidence: DocumentEvidence,
    ) -> tuple[int, str]:
        severity_order = {
            EvidenceSeverity.CRITICAL: 0,
            EvidenceSeverity.HIGH: 1,
            EvidenceSeverity.MEDIUM: 2,
            EvidenceSeverity.LOW: 3,
            EvidenceSeverity.INFO: 4,
        }

        return (
            severity_order.get(
                evidence.severity,
                5,
            ),
            evidence.title.lower(),
        )