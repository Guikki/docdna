from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.config.settings import settings
from app.domain.models.batch import Batch
from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.services.batch_cross_validation_service import (
    BatchCrossValidationService,
)
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)


class BatchExcelExportService:

    SUMMARY_SHEET_NAME = "Resumo do lote"
    DOCUMENTS_SHEET_NAME = "Documentos"
    EVIDENCES_SHEET_NAME = "Evidências"
    COMPARISONS_SHEET_NAME = "Comparações do lote"

    def __init__(self) -> None:
        self._analysis_repository = AnalysisMemoryRepository()
        self._cross_validation_service = (
            BatchCrossValidationService()
        )

    def export(
        self,
        batch: Batch,
    ) -> dict[str, Any]:
        output_dir = settings.REPORTS_DIR / "batches"

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"docdna_lote_{str(batch.id)[:8]}.xlsx"
        )

        file_path = output_dir / filename

        workbook = Workbook()

        summary_sheet = workbook.active
        summary_sheet.title = self.SUMMARY_SHEET_NAME

        documents_sheet = workbook.create_sheet(
            self.DOCUMENTS_SHEET_NAME
        )

        evidences_sheet = workbook.create_sheet(
            self.EVIDENCES_SHEET_NAME
        )

        comparisons_sheet = workbook.create_sheet(
            self.COMPARISONS_SHEET_NAME
        )

        exported_documents = self._build_documents_sheet(
            worksheet=documents_sheet,
            batch=batch,
        )

        exported_evidences = self._build_evidences_sheet(
            worksheet=evidences_sheet,
            batch=batch,
        )

        evidence_report = (
            self._cross_validation_service
            .build_evidence_report(batch)
        )

        exported_comparisons = (
            self._build_comparisons_sheet(
                worksheet=comparisons_sheet,
                evidences=evidence_report.evidences,
            )
        )

        self._build_summary_sheet(
            worksheet=summary_sheet,
            batch=batch,
            exported_documents=exported_documents,
            exported_evidences=exported_evidences,
            exported_comparisons=exported_comparisons,
            highest_severity=(
                evidence_report.highest_severity
            ),
        )

        workbook.save(file_path)

        return {
            "batch_id": str(batch.id),
            "filename": filename,
            "file_path": str(file_path),
            "download_url": (
                f"/reports/batches/{filename}"
            ),
            "total_documents": (
                batch.result.total_documents
            ),
            "exported_documents": exported_documents,
            "exported_evidences": exported_evidences,
            "message": (
                "Relatório do lote exportado com sucesso."
            ),
        }

    def _build_summary_sheet(
        self,
        worksheet,
        batch: Batch,
        exported_documents: int,
        exported_evidences: int,
        exported_comparisons: int,
        highest_severity: EvidenceSeverity | None,
    ) -> None:
        worksheet.append(
            [
                "Campo",
                "Valor",
            ]
        )

        rows = [
            (
                "ID do lote",
                str(batch.id),
            ),
            (
                "Status",
                self._translate_batch_status(
                    batch.status.value
                ),
            ),
            (
                "Criado em",
                self._format_datetime(
                    batch.created_at
                ),
            ),
            (
                "Iniciado em",
                self._format_datetime(
                    batch.started_at
                ),
            ),
            (
                "Finalizado em",
                self._format_datetime(
                    batch.finished_at
                ),
            ),
            (
                "Total de documentos",
                batch.result.total_documents,
            ),
            (
                "Documentos concluídos",
                batch.result.completed_documents,
            ),
            (
                "Documentos com falha",
                batch.result.failed_documents,
            ),
            (
                "Documentos pendentes",
                batch.result.pending_documents,
            ),
            (
                "Documentos em processamento",
                batch.result.processing_documents,
            ),
            (
                "Progresso",
                f"{batch.result.progress_percentage:.2f}%",
            ),
            (
                "Documentos exportados",
                exported_documents,
            ),
            (
                "Evidências individuais exportadas",
                exported_evidences,
            ),
            (
                "Comparações do lote exportadas",
                exported_comparisons,
            ),
            (
                "Severidade comparativa predominante",
                (
                    self._translate_severity(
                        highest_severity
                    )
                    if highest_severity
                    else "Sem apontamentos"
                ),
            ),
        ]

        for row in rows:
            worksheet.append(row)

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=True,
        )

        worksheet.column_dimensions["A"].width = 38
        worksheet.column_dimensions["B"].width = 52

    def _build_documents_sheet(
        self,
        worksheet,
        batch: Batch,
    ) -> int:
        headers = [
            "Documento",
            "Status no lote",
            "ID da análise",
            "Tamanho em bytes",
            "SHA-256",
            "Páginas",
            "Título do PDF",
            "Autor do PDF",
            "Produtor do PDF",
            "Data de criação",
            "Data de modificação",
            "ITF",
            "QR Code",
            "Code 39",
            "Outros códigos",
            "Sequências numéricas",
            "Fontes das sequências",
            "Validações estruturais",
            "Comparações linha × código",
            "Total de evidências",
            "Status da localização visual",
            "Erro de processamento",
        ]

        worksheet.append(headers)

        exported_documents = 0

        for batch_document in batch.documents:
            analysis = self._get_analysis(
                batch_document.analysis_id
            )

            if analysis is None:
                worksheet.append(
                    [
                        batch_document.original_filename,
                        self._translate_document_status(
                            batch_document.status.value
                        ),
                        self._optional_uuid(
                            batch_document.analysis_id
                        ),
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0,
                        None,
                        batch_document.error_message,
                    ]
                )

                continue

            barcodes = analysis.get(
                "barcodes",
                [],
            )

            barcode_groups = self._group_barcodes(
                barcodes
            )

            printed_numeric_lines = analysis.get(
                "printed_numeric_lines",
                [],
            )

            numeric_line_validations = analysis.get(
                "numeric_line_validations",
                [],
            )

            barcode_line_comparisons = analysis.get(
                "barcode_line_comparisons",
                [],
            )

            numeric_line_locations = analysis.get(
                "numeric_line_locations",
                [],
            )

            evidences = analysis.get(
                "evidences",
                [],
            )

            pdf_info = analysis.get(
                "pdf_info"
            )

            worksheet.append(
                [
                    batch_document.original_filename,
                    self._translate_document_status(
                        batch_document.status.value
                    ),
                    self._optional_uuid(
                        batch_document.analysis_id
                    ),
                    analysis.get("size_bytes"),
                    analysis.get("sha256"),
                    self._safe_attribute(
                        pdf_info,
                        "page_count",
                    ),
                    self._safe_attribute(
                        pdf_info,
                        "title",
                    ),
                    self._safe_attribute(
                        pdf_info,
                        "author",
                    ),
                    self._safe_attribute(
                        pdf_info,
                        "producer",
                    ),
                    self._safe_attribute(
                        pdf_info,
                        "creation_date",
                    ),
                    self._safe_attribute(
                        pdf_info,
                        "modification_date",
                    ),
                    self._join_values(
                        barcode_groups["itf"]
                    ),
                    self._join_values(
                        barcode_groups["qr_code"]
                    ),
                    self._join_values(
                        barcode_groups["code_39"]
                    ),
                    self._join_values(
                        barcode_groups["others"]
                    ),
                    self._format_numeric_lines(
                        printed_numeric_lines
                    ),
                    self._format_numeric_line_sources(
                        printed_numeric_lines
                    ),
                    self._format_validations(
                        numeric_line_validations
                    ),
                    self._format_comparisons(
                        barcode_line_comparisons
                    ),
                    len(evidences),
                    self._format_locations(
                        numeric_line_locations
                    ),
                    batch_document.error_message,
                ]
            )

            exported_documents += 1

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=True,
        )

        self._set_documents_column_widths(
            worksheet
        )

        return exported_documents

    def _build_evidences_sheet(
        self,
        worksheet,
        batch: Batch,
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Código da evidência",
            "Título",
            "Descrição",
            "Severidade",
            "Detector",
            "Confiança",
        ]

        worksheet.append(headers)

        exported_evidences = 0

        for batch_document in batch.documents:
            analysis = self._get_analysis(
                batch_document.analysis_id
            )

            if analysis is None:
                continue

            evidences = analysis.get(
                "evidences",
                [],
            )

            for evidence in evidences:
                severity = self._enum_value(
                    self._safe_attribute(
                        evidence,
                        "severity",
                    )
                )

                confidence = self._safe_attribute(
                    evidence,
                    "confidence",
                )

                worksheet.append(
                    [
                        batch_document.original_filename,
                        self._optional_uuid(
                            batch_document.analysis_id
                        ),
                        self._safe_attribute(
                            evidence,
                            "code",
                        ),
                        self._safe_attribute(
                            evidence,
                            "title",
                        ),
                        self._safe_attribute(
                            evidence,
                            "description",
                        ),
                        self._translate_severity_value(
                            severity
                        ),
                        (
                            self._safe_attribute(
                                evidence,
                                "detector",
                            )
                            or self._safe_attribute(
                                evidence,
                                "source",
                            )
                        ),
                        self._format_confidence(
                            confidence
                        ),
                    ]
                )

                exported_evidences += 1

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=True,
        )

        column_widths = {
            "A": 38,
            "B": 38,
            "C": 30,
            "D": 42,
            "E": 70,
            "F": 18,
            "G": 44,
            "H": 16,
        }

        for column, width in column_widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

        return exported_evidences

    def _build_comparisons_sheet(
        self,
        worksheet,
        evidences: list[DocumentEvidence],
    ) -> int:
        headers = [
            "Código do apontamento",
            "Título",
            "Descrição",
            "Severidade",
            "Confiança",
            "Código ITF relacionado",
            "Quantidade de documentos",
            "Documentos envolvidos",
            "Sequências numéricas por documento",
            "Componente responsável",
        ]

        worksheet.append(headers)

        exported_comparisons = 0

        for evidence in evidences:
            metadata = dict(
                evidence.metadata
            )

            document_names = (
                self._extract_comparison_document_names(
                    metadata
                )
            )

            numeric_lines_by_document = (
                self._format_comparison_numeric_lines(
                    metadata
                )
            )

            worksheet.append(
                [
                    evidence.code,
                    evidence.title,
                    evidence.description,
                    self._translate_severity(
                        evidence.severity
                    ),
                    self._format_confidence(
                        evidence.confidence
                    ),
                    metadata.get("itf"),
                    (
                        metadata.get(
                            "document_count"
                        )
                        or len(
                            evidence.document_ids
                        )
                    ),
                    self._join_values(
                        document_names
                    ),
                    numeric_lines_by_document,
                    evidence.source,
                ]
            )

            exported_comparisons += 1

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=True,
        )

        column_widths = {
            "A": 42,
            "B": 52,
            "C": 80,
            "D": 18,
            "E": 16,
            "F": 60,
            "G": 24,
            "H": 54,
            "I": 80,
            "J": 52,
        }

        for column, width in column_widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

        return exported_comparisons

    def _extract_comparison_document_names(
        self,
        metadata: dict[str, Any],
    ) -> list[str]:
        document_names = metadata.get(
            "document_names",
            [],
        )

        if isinstance(document_names, list):
            normalized_names = [
                str(name).strip()
                for name in document_names
                if str(name).strip()
            ]

            if normalized_names:
                return normalized_names

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

    def _format_comparison_numeric_lines(
        self,
        metadata: dict[str, Any],
    ) -> str:
        documents = metadata.get(
            "documents",
            [],
        )

        if not isinstance(documents, list):
            return ""

        formatted_documents: list[str] = []

        for document in documents:
            if not isinstance(document, dict):
                continue

            filename = str(
                document.get(
                    "filename",
                    "Documento sem nome",
                )
            ).strip()

            numeric_lines = document.get(
                "numeric_lines",
                [],
            )

            if not isinstance(numeric_lines, list):
                numeric_lines = [
                    numeric_lines
                ]

            normalized_lines = self._join_values(
                numeric_lines
            )

            if not normalized_lines:
                normalized_lines = (
                    "Nenhuma sequência registrada"
                )

            formatted_documents.append(
                f"{filename}: {normalized_lines}"
            )

        return "\n\n".join(
            formatted_documents
        )

    def _get_analysis(
        self,
        analysis_id,
    ) -> dict[str, Any] | None:
        if analysis_id is None:
            return None

        return self._analysis_repository.get_by_id(
            analysis_id
        )

    def _group_barcodes(
        self,
        barcodes: list[Any],
    ) -> dict[str, list[str]]:
        grouped = {
            "itf": [],
            "qr_code": [],
            "code_39": [],
            "others": [],
        }

        for barcode in barcodes:
            content = str(
                self._safe_attribute(
                    barcode,
                    "content",
                )
                or ""
            ).strip()

            barcode_format = str(
                self._safe_attribute(
                    barcode,
                    "format",
                )
                or ""
            ).strip()

            normalized_format = (
                barcode_format
                .lower()
                .replace("-", "")
                .replace("_", "")
                .replace(" ", "")
            )

            if not content:
                continue

            if "itf" in normalized_format:
                grouped["itf"].append(
                    content
                )
                continue

            if (
                "qr" in normalized_format
                or "qrcode" in normalized_format
            ):
                grouped["qr_code"].append(
                    content
                )
                continue

            if (
                "code39" in normalized_format
                or normalized_format == "39"
            ):
                grouped["code_39"].append(
                    content
                )
                continue

            grouped["others"].append(
                f"{barcode_format}: {content}"
            )

        return grouped

    def _format_numeric_lines(
        self,
        lines: list[Any],
    ) -> str:
        values = [
            str(
                self._safe_attribute(
                    line,
                    "normalized_content",
                )
                or ""
            )
            for line in lines
        ]

        return self._join_values(values)

    def _format_numeric_line_sources(
        self,
        lines: list[Any],
    ) -> str:
        values = [
            str(
                self._safe_attribute(
                    line,
                    "source",
                )
                or ""
            )
            for line in lines
        ]

        return self._join_values(values)

    def _format_validations(
        self,
        validations: list[Any],
    ) -> str:
        formatted_values: list[str] = []

        for validation in validations:
            status = self._enum_value(
                self._safe_attribute(
                    validation,
                    "status",
                )
            )

            line_type = self._enum_value(
                self._safe_attribute(
                    validation,
                    "line_type",
                )
            )

            valid_digits = self._safe_attribute(
                validation,
                "valid_check_digits",
            )

            total_digits = self._safe_attribute(
                validation,
                "total_check_digits",
            )

            formatted_values.append(
                (
                    f"Sequência "
                    f"{self._safe_attribute(validation, 'line_index')}: "
                    f"{status}; "
                    f"tipo={line_type}; "
                    f"dígitos verificadores="
                    f"{valid_digits}/{total_digits}"
                )
            )

        return self._join_values(
            formatted_values
        )

    def _format_comparisons(
        self,
        comparisons: list[Any],
    ) -> str:
        formatted_values: list[str] = []

        for comparison in comparisons:
            status = self._enum_value(
                self._safe_attribute(
                    comparison,
                    "status",
                )
            )

            converted_barcode = self._safe_attribute(
                comparison,
                "converted_barcode",
            )

            detected_barcode = self._safe_attribute(
                comparison,
                "detected_barcode",
            )

            formatted_values.append(
                (
                    f"Sequência "
                    f"{self._safe_attribute(comparison, 'line_index')}: "
                    f"{status}; "
                    f"calculado={converted_barcode or '-'}; "
                    f"detectado={detected_barcode or '-'}"
                )
            )

        return self._join_values(
            formatted_values
        )

    def _format_locations(
        self,
        locations: list[Any],
    ) -> str:
        formatted_values: list[str] = []

        for location in locations:
            located = bool(
                self._safe_attribute(
                    location,
                    "located",
                )
            )

            if located:
                formatted_values.append(
                    (
                        f"Sequência "
                        f"{self._safe_attribute(location, 'line_index')}: "
                        f"localizada na página "
                        f"{self._safe_attribute(location, 'page_number')}"
                    )
                )
            else:
                formatted_values.append(
                    (
                        f"Sequência "
                        f"{self._safe_attribute(location, 'line_index')}: "
                        "não localizada"
                    )
                )

        return self._join_values(
            formatted_values
        )

    def _style_worksheet(
        self,
        worksheet,
        freeze_panes: str,
        auto_filter: bool,
    ) -> None:
        header_fill = PatternFill(
            fill_type="solid",
            fgColor="24184F",
        )

        header_font = Font(
            color="FFFFFF",
            bold=True,
        )

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        worksheet.row_dimensions[1].height = 32

        for row in worksheet.iter_rows(
            min_row=2,
        ):
            for cell in row:
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

        worksheet.freeze_panes = freeze_panes

        if auto_filter:
            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

        worksheet.sheet_view.showGridLines = False

    def _set_documents_column_widths(
        self,
        worksheet,
    ) -> None:
        widths = [
            38,
            18,
            38,
            18,
            68,
            12,
            30,
            26,
            30,
            24,
            24,
            54,
            70,
            34,
            52,
            70,
            24,
            70,
            80,
            18,
            44,
            46,
        ]

        for index, width in enumerate(
            widths,
            start=1,
        ):
            column_letter = get_column_letter(
                index
            )

            worksheet.column_dimensions[
                column_letter
            ].width = width

    def _format_datetime(
        self,
        value,
    ) -> str:
        if value is None:
            return "Não informada"

        return value.strftime(
            "%d/%m/%Y às %H:%M:%S"
        )

    def _format_confidence(
        self,
        value: Any,
    ) -> str:
        if value is None:
            return "Não informada"

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return str(value)

        confidence = min(
            max(confidence, 0.0),
            1.0,
        )

        return f"{confidence * 100:.0f}%"

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

    def _translate_severity_value(
        self,
        severity: Any,
    ) -> str:
        normalized_severity = str(
            severity or ""
        ).strip().lower()

        labels = {
            "critical": "Crítico",
            "high": "Alto",
            "medium": "Médio",
            "low": "Baixo",
            "info": "Informativo",
        }

        return labels.get(
            normalized_severity,
            normalized_severity or "Não classificado",
        )

    def _translate_batch_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando processamento",
            "processing": "Em processamento",
            "completed": "Concluído",
            "completed_with_errors": (
                "Concluído com ocorrências"
            ),
            "failed": "Falhou",
        }

        return labels.get(
            status,
            status,
        )

    def _translate_document_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando",
            "processing": "Em processamento",
            "completed": "Concluído",
            "failed": "Falhou",
        }

        return labels.get(
            status,
            status,
        )

    def _optional_uuid(
        self,
        value,
    ) -> str | None:
        if value is None:
            return None

        return str(value)

    def _safe_attribute(
        self,
        value: Any,
        attribute: str,
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, dict):
            return value.get(
                attribute
            )

        return getattr(
            value,
            attribute,
            None,
        )

    def _enum_value(
        self,
        value: Any,
    ) -> Any:
        if value is None:
            return None

        return getattr(
            value,
            "value",
            value,
        )

    def _join_values(
        self,
        values: list[Any],
    ) -> str:
        normalized_values: list[str] = []

        for value in values:
            if value is None:
                continue

            normalized_value = str(
                value
            ).strip()

            if (
                not normalized_value
                or normalized_value
                in normalized_values
            ):
                continue

            normalized_values.append(
                normalized_value
            )

        return "\n".join(
            normalized_values
        )