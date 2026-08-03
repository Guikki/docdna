from typing import Any

from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.models.evidence_report import EvidenceReport

from app.frontend.view_models.evidence_presentation_catalog import (
    EVIDENCE_PRESENTATION_CATALOG,
)

class ComparisonViewBuilder:

    def build(
        self,
        report: EvidenceReport,
        batch_view: dict[str, Any],
    ) -> dict[str, Any]:
        evidences = [
            self._build_evidence_view(
                evidence=evidence,
                batch_view=batch_view,
            )
            for evidence in report.evidences
        ]

        related_document_ids = self._collect_related_document_ids(
            report
        )

        return {
            "batch_id": batch_view["id"],
            "batch_status": batch_view["status"],
            "batch_status_label": batch_view["status_label"],
            "batch_created_at": batch_view["created_at"],
            "batch_finished_at": batch_view["finished_at"],
            "batch_url": (
                f"/batches/{batch_view['id']}"
            ),
            "total_documents": (
                batch_view["result"]["total_documents"]
            ),
            "total_findings": report.total,
            "has_findings": report.has_evidences,
            "critical": report.critical,
            "high": report.high,
            "medium": report.medium,
            "low": report.low,
            "info": report.info,
            "highest_severity": (
                report.highest_severity.value
                if report.highest_severity
                else None
            ),
            "highest_severity_label": (
                self._translate_severity(
                    report.highest_severity
                )
                if report.highest_severity
                else "Sem apontamentos"
            ),
            "related_document_count": len(
                related_document_ids
            ),
            "summary_message": self._build_summary_message(
                report=report,
                related_document_count=len(
                    related_document_ids
                ),
            ),
            "evidences": evidences,
        }

    def _build_evidence_view(
        self,
        evidence: DocumentEvidence,
        batch_view: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = dict(
            evidence.metadata
        )

        related_documents = self._build_related_documents(
            document_ids=evidence.document_ids,
            metadata=metadata,
            batch_view=batch_view,
        )

        presentation = EVIDENCE_PRESENTATION_CATALOG.get(
            evidence.code,
            {
                "category": "Evidência Técnica",
                "display_title": evidence.title,
                "method_label": "Análise comparativa documental",
            },
        )

        technical_details = self._build_technical_details(
            metadata
        )

        compared_elements = self._build_compared_elements(
            metadata
        )

        return {
            "code": evidence.code,
            "source": evidence.source,
            "category": presentation["category"],
            "title": presentation["display_title"],
            "method_label": presentation["method_label"],
            "description": evidence.description,
            "severity": evidence.severity.value,
            "severity_label": self._translate_severity(
                evidence.severity
            ),
            "confidence": evidence.confidence,
            "confidence_label": self._format_confidence(
                evidence.confidence
            ),
            "itf": metadata.get("itf"),
            "document_count": len(
                related_documents
            ),
            "documents": related_documents,
            "numeric_lines_by_document": (
                self._build_numeric_lines_by_document(
                    metadata
                )
            ),
            "technical_details": technical_details,
            "compared_elements": compared_elements,
            "has_technical_details": bool(
                technical_details
                or compared_elements
            ),
            "metadata": metadata,
        }

    def _build_technical_details(
        self,
        metadata: dict[str, Any],
    ) -> list[dict[str, str]]:
        detail_definitions = [
            (
                "classification",
                "Classificação técnica",
                self._translate_classification,
            ),
            (
                "perceptual_similarity",
                "Similaridade perceptual",
                self._format_percentage_value,
            ),
            (
                "average_similarity",
                "Similaridade média",
                self._format_percentage_value,
            ),
            (
                "difference_similarity",
                "Similaridade diferencial",
                self._format_percentage_value,
            ),
            (
                "exact_image_match",
                "Imagem exatamente igual",
                self._format_boolean,
            ),
            (
                "same_dimensions",
                "Mesmas dimensões",
                self._format_boolean,
            ),
            (
                "same_company_name",
                "Mesmo nome de empresa",
                self._format_optional_boolean,
            ),
            (
                "same_value",
                "Mesmo conteúdo decodificado",
                self._format_boolean,
            ),
            (
                "same_encoding",
                "Mesma codificação",
                self._format_optional_boolean,
            ),
            (
                "same_version",
                "Mesma versão",
                self._format_optional_boolean,
            ),
            (
                "same_error_correction",
                "Mesma correção de erro",
                self._format_optional_boolean,
            ),
            (
                "rotation_difference",
                "Diferença de rotação",
                self._format_rotation,
            ),
            (
                "width_difference",
                "Diferença de largura",
                self._format_pixels,
            ),
            (
                "height_difference",
                "Diferença de altura",
                self._format_pixels,
            ),
        ]

        details: list[dict[str, str]] = []

        for key, label, formatter in detail_definitions:
            if key not in metadata:
                continue

            value = metadata.get(key)

            if value is None:
                continue

            details.append(
                {
                    "key": key,
                    "label": label,
                    "value": formatter(value),
                }
            )

        return details

    def _build_compared_elements(
        self,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        pairs = [
            (
                "first_image",
                "second_image",
                "Imagem A",
                "Imagem B",
                "image",
            ),
            (
                "first_logo",
                "second_logo",
                "Logo A",
                "Logo B",
                "logo",
            ),
            (
                "first_qrcode",
                "second_qrcode",
                "QR Code A",
                "QR Code B",
                "qrcode",
            ),
        ]

        elements: list[dict[str, Any]] = []

        for (
            first_key,
            second_key,
            first_label,
            second_label,
            element_type,
        ) in pairs:
            first_value = metadata.get(first_key)
            second_value = metadata.get(second_key)

            if not isinstance(first_value, dict):
                continue

            if not isinstance(second_value, dict):
                continue

            elements.extend(
                [
                    self._build_element_view(
                        label=first_label,
                        element_type=element_type,
                        data=first_value,
                    ),
                    self._build_element_view(
                        label=second_label,
                        element_type=element_type,
                        data=second_value,
                    ),
                ]
            )

            break

        return elements

    def _build_element_view(
        self,
        *,
        label: str,
        element_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        fields: list[dict[str, str]] = []

        field_definitions = [
            ("page_number", "Página", str),
            ("company_name", "Empresa", self._format_text),
            ("value", "Conteúdo", self._format_text),
            ("encoding", "Codificação", self._format_text),
            ("version", "Versão", self._format_text),
            (
                "error_correction",
                "Correção de erro",
                self._format_text,
            ),
            ("rotation", "Rotação", self._format_rotation),
            ("width", "Largura", self._format_pixels),
            ("height", "Altura", self._format_pixels),
            ("mime_type", "Tipo", self._format_text),
        ]

        for key, field_label, formatter in field_definitions:
            value = data.get(key)

            if value is None or value == "":
                continue

            fields.append(
                {
                    "label": field_label,
                    "value": formatter(value),
                    "break_value": key == "value",
                }
            )

        hashes = [
            {
                "label": "SHA-256 da imagem",
                "value": str(data["image_hash"]),
            }
            for _ in [0]
            if data.get("image_hash")
        ]

        return {
            "label": label,
            "type": element_type,
            "fields": fields,
            "hashes": hashes,
        }

    def _translate_classification(
        self,
        value: Any,
    ) -> str:
        labels = {
            "exact": "Correspondência exata",
            "strong": "Forte correspondência",
            "visual": "Correspondência visual",
            "moderate": "Correspondência moderada",
            "none": "Sem correspondência",
        }

        normalized = str(value).strip().lower()

        return labels.get(
            normalized,
            str(value),
        )

    def _format_percentage_value(
        self,
        value: Any,
    ) -> str:
        try:
            normalized = min(
                max(float(value), 0.0),
                1.0,
            )
        except (TypeError, ValueError):
            return str(value)

        return f"{normalized * 100:.1f}%"

    def _format_boolean(
        self,
        value: Any,
    ) -> str:
        return "Sim" if bool(value) else "Não"

    def _format_optional_boolean(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return "Não disponível"

        return self._format_boolean(value)

    def _format_pixels(
        self,
        value: Any,
    ) -> str:
        return f"{value} px"

    def _format_rotation(
        self,
        value: Any,
    ) -> str:
        return f"{value}°"

    def _format_text(
        self,
        value: Any,
    ) -> str:
        normalized = str(value).strip()

        return normalized or "Não informado"

    def _build_related_documents(
        self,
        document_ids: list[str],
        metadata: dict[str, Any],
        batch_view: dict[str, Any],
    ) -> list[dict[str, Any]]:
        batch_documents = batch_view.get(
            "documents",
            [],
        )

        documents_by_analysis_id = {
            str(document.get("analysis_id")): document
            for document in batch_documents
            if document.get("analysis_id")
        }

        metadata_names = self._extract_document_names(
            metadata
        )

        related_documents: list[dict[str, Any]] = []

        for index, document_id in enumerate(
            document_ids
        ):
            document = documents_by_analysis_id.get(
                str(document_id)
            )

            if document:
                related_documents.append(
                    {
                        "analysis_id": str(
                            document_id
                        ),
                        "filename": document.get(
                            "original_filename",
                            "Documento sem nome",
                        ),
                        "analysis_url": document.get(
                            "analysis_url"
                        ),
                        "status": document.get(
                            "status"
                        ),
                        "status_label": document.get(
                            "status_label"
                        ),
                    }
                )

                continue

            filename = (
                metadata_names[index]
                if index < len(metadata_names)
                else "Documento sem nome"
            )

            related_documents.append(
                {
                    "analysis_id": str(
                        document_id
                    ),
                    "filename": filename,
                    "analysis_url": (
                        f"/analyses/{document_id}"
                    ),
                    "status": None,
                    "status_label": None,
                }
            )

        return related_documents

    def _build_numeric_lines_by_document(
        self,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        documents = metadata.get(
            "documents",
            [],
        )

        if not isinstance(documents, list):
            return []

        result: list[dict[str, Any]] = []

        for document in documents:
            if not isinstance(document, dict):
                continue

            numeric_lines = document.get(
                "numeric_lines",
                [],
            )

            if not isinstance(numeric_lines, list):
                numeric_lines = [
                    numeric_lines
                ]

            normalized_lines = [
                str(line).strip()
                for line in numeric_lines
                if str(line).strip()
            ]

            result.append(
                {
                    "analysis_id": str(
                        document.get(
                            "analysis_id",
                            "",
                        )
                    ),
                    "filename": str(
                        document.get(
                            "filename",
                            "Documento sem nome",
                        )
                    ),
                    "numeric_lines": normalized_lines,
                }
            )

        return result

    def _extract_document_names(
        self,
        metadata: dict[str, Any],
    ) -> list[str]:
        document_names = metadata.get(
            "document_names",
            [],
        )

        if isinstance(document_names, list):
            names = [
                str(name).strip()
                for name in document_names
                if str(name).strip()
            ]

            if names:
                return names

        documents = metadata.get(
            "documents",
            [],
        )

        if not isinstance(documents, list):
            return []

        return [
            str(
                document.get(
                    "filename",
                    "Documento sem nome",
                )
            )
            for document in documents
            if isinstance(document, dict)
        ]

    def _collect_related_document_ids(
        self,
        report: EvidenceReport,
    ) -> set[str]:
        document_ids: set[str] = set()

        for evidence in report.evidences:
            document_ids.update(
                str(document_id)
                for document_id in evidence.document_ids
            )

        return document_ids

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

        return (
            f"{normalized_confidence * 100:.0f}%"
        )

    def _build_summary_message(
        self,
        report: EvidenceReport,
        related_document_count: int,
    ) -> str:
        if not report.has_evidences:
            return (
                "Nenhum apontamento comparativo relevante foi "
                "identificado entre os documentos deste lote."
            )

        finding_label = (
            "apontamento comparativo"
            if report.total == 1
            else "apontamentos comparativos"
        )

        document_label = (
            "documento relacionado"
            if related_document_count == 1
            else "documentos relacionados"
        )

        severity_label = (
            self._translate_severity(
                report.highest_severity
            ).lower()
            if report.highest_severity
            else "não classificada"
        )

        return (
            f"Foram identificados {report.total} "
            f"{finding_label}, envolvendo "
            f"{related_document_count} "
            f"{document_label}. "
            f"A severidade predominante é "
            f"{severity_label}."
        )