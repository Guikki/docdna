from collections import defaultdict
from typing import Any

from app.domain.comparators.base_comparator import BaseComparator
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)


class DuplicateItfComparator(BaseComparator):

    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        grouped_itfs: dict[
            str,
            dict[str, dict[str, Any]],
        ] = defaultdict(dict)

        for analysis in analyses:
            analysis_id = str(
                analysis.get("id", "")
            )

            if not analysis_id:
                continue

            barcodes = analysis.get(
                "barcodes",
                [],
            )

            for barcode in barcodes:
                barcode_format = self._normalize_format(
                    getattr(
                        barcode,
                        "format",
                        "",
                    )
                )

                if "itf" not in barcode_format:
                    continue

                content = self._normalize_content(
                    getattr(
                        barcode,
                        "content",
                        "",
                    )
                )

                if not content:
                    continue

                grouped_itfs[content][analysis_id] = analysis

        findings: list[CrossValidationFinding] = []

        for itf, documents_by_id in grouped_itfs.items():
            documents = list(
                documents_by_id.values()
            )

            if len(documents) < 2:
                continue

            document_ids = [
                str(document["id"])
                for document in documents
            ]

            document_names = [
                str(
                    document.get(
                        "original_filename",
                        "Documento sem nome",
                    )
                )
                for document in documents
            ]

            findings.append(
                CrossValidationFinding(
                    code="DUPLICATE_ITF",
                    title="Código ITF repetido",
                    description=(
                        "O mesmo conteúdo ITF foi identificado "
                        f"em {len(documents)} documentos distintos "
                        "do lote."
                    ),
                    severity=CrossValidationSeverity.INFO,
                    confidence=1.0,
                    comparator=self.__class__.__name__,
                    document_ids=document_ids,
                    metadata={
                        "itf": itf,
                        "document_count": len(documents),
                        "document_names": document_names,
                    },
                )
            )

        return findings

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

    def _normalize_content(
        self,
        value: Any,
    ) -> str:
        return "".join(
            character
            for character in str(value or "")
            if character.isalnum()
        )