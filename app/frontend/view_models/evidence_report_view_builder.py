from typing import Any

from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.models.evidence_report import EvidenceReport


class EvidenceReportViewBuilder:

    def build(
        self,
        report: EvidenceReport,
    ) -> dict[str, Any]:
        highest_severity = report.highest_severity

        return {
            "total": report.total,
            "has_evidences": report.has_evidences,
            "critical": report.critical,
            "high": report.high,
            "medium": report.medium,
            "low": report.low,
            "info": report.info,
            "highest_severity": (
                highest_severity.value
                if highest_severity
                else None
            ),
            "highest_severity_label": (
                self._translate_severity(
                    highest_severity
                )
                if highest_severity
                else "Sem apontamentos"
            ),
            "summary_message": self._build_summary_message(
                report
            ),
            "evidences": [
                self._build_evidence_view(evidence)
                for evidence in report.evidences
            ],
        }

    def _build_evidence_view(
        self,
        evidence: DocumentEvidence,
    ) -> dict[str, Any]:
        metadata = dict(evidence.metadata)

        return {
            "code": evidence.code,
            "title": evidence.title,
            "description": evidence.description,
            "severity": evidence.severity.value,
            "severity_label": self._translate_severity(
                evidence.severity
            ),
            "confidence": evidence.confidence,
            "confidence_label": self._format_confidence(
                evidence.confidence
            ),
            "source": evidence.source,
            "document_ids": list(
                evidence.document_ids
            ),
            "document_count": len(
                evidence.document_ids
            ),
            "document_names": self._extract_document_names(
                metadata
            ),
            "itf": metadata.get("itf"),
            "metadata": metadata,
        }

    def _translate_severity(
        self,
        severity: EvidenceSeverity,
    ) -> str:
        labels = {
            EvidenceSeverity.CRITICAL: "Crítico",
            EvidenceSeverity.HIGH: "Alto",
            EvidenceSeverity.MEDIUM: "Médio",
            EvidenceSeverity.LOW: "Baixo",
            EvidenceSeverity.INFO: "Informativo",
        }

        return labels.get(
            severity,
            "Não classificado",
        )

    def _format_confidence(
        self,
        confidence: float,
    ) -> str:
        normalized_confidence = min(
            max(float(confidence), 0.0),
            1.0,
        )

        return f"{normalized_confidence * 100:.0f}%"

    def _extract_document_names(
        self,
        metadata: dict[str, Any],
    ) -> list[str]:
        document_names = metadata.get(
            "document_names",
            [],
        )

        if isinstance(document_names, list):
            return [
                str(name)
                for name in document_names
                if str(name).strip()
            ]

        documents = metadata.get(
            "documents",
            [],
        )

        if not isinstance(documents, list):
            return []

        names: list[str] = []

        for document in documents:
            if not isinstance(document, dict):
                continue

            filename = str(
                document.get(
                    "filename",
                    "",
                )
            ).strip()

            if filename and filename not in names:
                names.append(filename)

        return names

    def _build_summary_message(
        self,
        report: EvidenceReport,
    ) -> str:
        if not report.has_evidences:
            return (
                "Nenhum apontamento comparativo foi identificado "
                "entre os documentos deste lote."
            )

        if report.critical > 0:
            return (
                "Foram identificados apontamentos comparativos "
                "de nível crítico que exigem verificação prioritária."
            )

        if report.high > 0:
            return (
                "Foram identificados apontamentos comparativos "
                "de nível alto que merecem análise detalhada."
            )

        if report.medium > 0:
            return (
                "Foram identificados apontamentos comparativos "
                "de nível médio para revisão."
            )

        if report.low > 0:
            return (
                "Foram identificados apontamentos comparativos "
                "de baixo impacto."
            )

        return (
            "O lote contém apontamentos comparativos "
            "de caráter informativo."
        )