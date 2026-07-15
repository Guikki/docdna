from collections import defaultdict
from typing import Any

from app.domain.comparators.base_comparator import BaseComparator
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)


class DuplicateItfDifferentNumericLineComparator(
    BaseComparator
):

    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        grouped_documents: dict[
            str,
            dict[str, dict[str, Any]],
        ] = defaultdict(dict)

        for analysis in analyses:
            analysis_id = str(
                analysis.get("id", "")
            ).strip()

            if not analysis_id:
                continue

            itfs = self._extract_itfs(analysis)

            if not itfs:
                continue

            numeric_lines = self._extract_numeric_lines(
                analysis
            )

            document_data = {
                "analysis_id": analysis_id,
                "filename": str(
                    analysis.get(
                        "original_filename",
                        "Documento sem nome",
                    )
                ),
                "numeric_lines": numeric_lines,
            }

            for itf in itfs:
                grouped_documents[itf][
                    analysis_id
                ] = document_data

        findings: list[CrossValidationFinding] = []

        for itf, documents_by_id in (
            grouped_documents.items()
        ):
            documents = list(
                documents_by_id.values()
            )

            if len(documents) < 2:
                continue

            documents_with_lines = [
                document
                for document in documents
                if document["numeric_lines"]
            ]

            if len(documents_with_lines) < 2:
                continue

            numeric_line_signatures = {
                tuple(document["numeric_lines"])
                for document in documents_with_lines
            }

            if len(numeric_line_signatures) < 2:
                continue

            document_ids = [
                document["analysis_id"]
                for document in documents_with_lines
            ]

            document_names = [
                document["filename"]
                for document in documents_with_lines
            ]

            findings.append(
                CrossValidationFinding(
                    code=(
                        "DUPLICATE_ITF_DIFFERENT_"
                        "NUMERIC_LINE"
                    ),
                    title=(
                        "Código ITF repetido com "
                        "sequências numéricas distintas"
                    ),
                    description=(
                        "O mesmo conteúdo ITF foi identificado "
                        "em documentos diferentes do lote, mas "
                        "as sequências numéricas capturadas nesses "
                        "documentos não são iguais. Esse padrão pode "
                        "indicar reutilização do código de barras "
                        "associada à alteração da representação "
                        "numérica visível."
                    ),
                    severity=CrossValidationSeverity.HIGH,
                    confidence=1.0,
                    comparator=self.__class__.__name__,
                    document_ids=document_ids,
                    metadata={
                        "itf": itf,
                        "document_count": len(
                            documents_with_lines
                        ),
                        "document_names": document_names,
                        "documents": documents_with_lines,
                    },
                )
            )

        return findings

    def _extract_itfs(
        self,
        analysis: dict[str, Any],
    ) -> list[str]:
        values: list[str] = []

        for barcode in analysis.get(
            "barcodes",
            [],
        ):
            barcode_format = self._normalize_format(
                self._read_value(
                    barcode,
                    "format",
                )
            )

            if "itf" not in barcode_format:
                continue

            content = self._normalize_alphanumeric(
                self._read_value(
                    barcode,
                    "content",
                )
            )

            if content and content not in values:
                values.append(content)

        return values

    def _extract_numeric_lines(
        self,
        analysis: dict[str, Any],
    ) -> list[str]:
        values: list[str] = []

        for line in analysis.get(
            "printed_numeric_lines",
            [],
        ):
            content = self._normalize_digits(
                self._read_value(
                    line,
                    "normalized_content",
                )
            )

            if content and content not in values:
                values.append(content)

        return sorted(values)

    def _read_value(
        self,
        source: Any,
        field: str,
    ) -> Any:
        if isinstance(source, dict):
            return source.get(field)

        return getattr(
            source,
            field,
            None,
        )

    def _normalize_format(
        self,
        value: Any,
    ) -> str:
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )

    def _normalize_alphanumeric(
        self,
        value: Any,
    ) -> str:
        return "".join(
            character
            for character in str(value or "")
            if character.isalnum()
        )

    def _normalize_digits(
        self,
        value: Any,
    ) -> str:
        return "".join(
            character
            for character in str(value or "")
            if character.isdigit()
        )