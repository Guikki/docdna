import json
import re
from hashlib import sha256
from math import isfinite

from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import (
    Table,
    TableStyleInfo,
)

from app.config.settings import settings
from app.domain.models.batch import Batch
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)
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
from app.domain.services.batch_finding_aggregation_service import (
    BatchFindingAggregationService,
)
from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.frontend.exports.batch_export_view_builder import (
    BatchExportViewBuilder,
)
from app.frontend.investigations.builders.investigation_view_builder import (
    InvestigationViewBuilder,
)
from app.frontend.investigations.services.investigation_status_resolver import (
    InvestigationStatusResolver,
)
from app.frontend.view_models.analysis_view_builder import (
    AnalysisViewBuilder,
)


class BatchExcelExportService:

    SUMMARY_SHEET_NAME = "00 - Resumo"
    TRIAGE_SHEET_NAME = "00 - Resumo"  # Triagem integrada ao resumo
    DOCUMENTS_SHEET_NAME = "01 - Documentos"
    FINDINGS_SHEET_NAME = "02 - Achados por tipo"
    EVIDENCES_SHEET_NAME = "03 - Evidências"
    FINANCIAL_SHEET_NAME = "04 - Financeiro"
    FINANCIAL_RECONCILIATION_SHEET_NAME = "04 - Financeiro"  # Reconciliação integrada
    PROMPT_INJECTION_SHEET_NAME = "05 - Prompt Injection"
    CONCEALMENT_SHEET_NAME = "06 - Ocultação visual"
    LOCATIONS_SHEET_NAME = "07 - Localizações"
    COMPARISONS_SHEET_NAME = "08 - Comparações"
    TECHNICAL_DATA_SHEET_NAME = "09 - Dados técnicos"
    IMAGES_SHEET_NAME = "10 - Imagens"
    # Caracteres de controle que não podem ser gravados
    # diretamente em células de arquivos XLSX/XML.
    #
    # TAB (\x09), LF (\x0A) e CR (\x0D) são permitidos
    # e, portanto, não fazem parte desta expressão.
    _EXCEL_ILLEGAL_CHARACTERS = re.compile(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
    )

    def __init__(self) -> None:
        self._current_identifier_observations: list[dict[str, Any]] = []
        self._analysis_repository = (
            AnalysisMemoryRepository()
        )

        self._cross_validation_service = (
            BatchCrossValidationService()
        )

        self._finding_aggregation_service = (
            BatchFindingAggregationService()
        )

        self._analysis_view_builder = (
            AnalysisViewBuilder()
        )

        self._investigation_view_builder = (
            InvestigationViewBuilder()
        )

        self._status_resolver = (
            InvestigationStatusResolver()
        )

        self._export_view_builder = (
            BatchExportViewBuilder()
        )

    def export(
        self,
        batch: Batch,
    ) -> dict[str, Any]:
        output_dir = (
            settings.REPORTS_DIR
            / "batches"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"docdna_lote_"
            f"{str(batch.id)[:8]}"
            f".xlsx"
        )

        file_path = (
            output_dir
            / filename
        )

        # Os mesmos achados comparativos alimentam a visão documental
        # e a aba de comparações. A validação cruzada roda uma única vez.
        (
            cross_validation_result,
            evidence_report,
        ) = self._cross_validation_service.execute_with_report(
            batch
        )

        export_view = (
            self._build_export_view(
                batch,
                comparative_findings=cross_validation_result.findings,
                identifier_comparisons=getattr(
                    self._cross_validation_service, "identifier_comparisons", []
                ),
            )
        )

        # A análise pode preservar caracteres de controle encontrados
        # no documento original. Alguns deles são inválidos no XML
        # utilizado internamente pelo formato XLSX.
        #
        # A sanitização acontece somente na representação destinada
        # à exportação. Os dados analíticos originais não são alterados.
        export_view = (
            self._sanitize_excel_payload(
                export_view
            )
        )

        # A reconciliação já foi produzida no processamento individual.
        # A exportação apenas a consulta; NÃO executa detectores nem reabre PDFs.
        financial_reconciliations = (
            self._build_financial_reconciliation_records(batch)
        )

        # A triagem usa exclusivamente resultados já produzidos.
        # Não cria novos diagnósticos e não altera a prioridade individual.
        triage_records = self._sanitize_excel_payload(
            self._build_triage_records(
                batch=batch,
                export_view=export_view,
                comparative_evidences=evidence_report.evidences,
                financial_reconciliations=financial_reconciliations,
            )
        )
        triage_by_analysis_id = {
            str(record["analysis_id"]): record
            for record in triage_records
            if record.get("analysis_id")
        }

        workbook = Workbook()

        summary_sheet = workbook.active
        summary_sheet.title = (
            self.SUMMARY_SHEET_NAME
        )

        documents_sheet = workbook.create_sheet(
            self.DOCUMENTS_SHEET_NAME
        )
        findings_sheet = workbook.create_sheet(
            self.FINDINGS_SHEET_NAME
        )
        evidences_sheet = workbook.create_sheet(
            self.EVIDENCES_SHEET_NAME
        )
        financial_sheet = workbook.create_sheet(
            self.FINANCIAL_SHEET_NAME
        )
        prompt_injection_sheet = workbook.create_sheet(
            self.PROMPT_INJECTION_SHEET_NAME
        )
        concealment_sheet = workbook.create_sheet(
            self.CONCEALMENT_SHEET_NAME
        )
        locations_sheet = workbook.create_sheet(
            self.LOCATIONS_SHEET_NAME
        )
        comparisons_sheet = workbook.create_sheet(
            self.COMPARISONS_SHEET_NAME
        )
        technical_data_sheet = workbook.create_sheet(
            self.TECHNICAL_DATA_SHEET_NAME
        )
        images_sheet = workbook.create_sheet(
            self.IMAGES_SHEET_NAME
        )

        exported_documents = (
            self._build_documents_sheet(
                worksheet=documents_sheet,
                batch=batch,
                export_view=export_view,
                triage_by_analysis_id=triage_by_analysis_id,
            )
        )

        exported_findings = (
            self._build_findings_sheet(
                worksheet=findings_sheet,
                export_view=export_view,
            )
        )

        self._current_identifier_observations = export_view.get("identifier_observations", [])
        exported_evidences = (
            self._build_evidences_sheet(
                worksheet=evidences_sheet,
                batch=batch,
            )
        )

        exported_financial = (
            self._build_financial_sheet(
                worksheet=financial_sheet,
                export_view=export_view,
                batch=batch,
                reconciliation_records=financial_reconciliations,
            )
        )

        # Mantém a métrica de reconciliação sem criar uma aba adicional.
        # O resumo é uma linha; cada valor observado também é uma linha.
        exported_financial_reconciliation = sum(
            1 + len(entry.get("values", []))
            for entry in financial_reconciliations
        )

        exported_prompt_injection = (
            self._build_prompt_injection_sheet(
                worksheet=prompt_injection_sheet,
                export_view=export_view,
            )
        )

        exported_concealment = (
            self._build_concealment_sheet(
                worksheet=concealment_sheet,
                export_view=export_view,
            )
        )

        exported_locations = (
            self._build_locations_sheet(
                worksheet=locations_sheet,
                export_view=export_view,
            )
        )

        exported_technical_data = (
            self._build_technical_data_sheet(
                worksheet=technical_data_sheet,
                export_view=export_view,
            )
        )

        exported_images = (
            self._build_images_sheet(
                worksheet=images_sheet,
                export_view=export_view,
            )
        )

        exported_comparisons = (
            self._build_comparisons_sheet(
                worksheet=comparisons_sheet,
                evidences=(
                    evidence_report.evidences
                ),
                total_documents=(
                    batch.result.total_documents
                ),
                identifier_comparisons=export_view.get("identifier_comparisons", []),
            )
        )

        self._build_summary_sheet(
            worksheet=summary_sheet,
            export_view=export_view,
            exported_documents=exported_documents,
            exported_findings=exported_findings,
            exported_evidences=exported_evidences,
            exported_financial=exported_financial,
            exported_financial_reconciliation=exported_financial_reconciliation,
            financial_reconciliations=financial_reconciliations,
            exported_prompt_injection=(
                exported_prompt_injection
            ),
            exported_concealment=(
                exported_concealment
            ),
            exported_locations=exported_locations,
            exported_comparisons=exported_comparisons,
            exported_technical_data=(
                exported_technical_data
            ),
            exported_images=exported_images,
            highest_severity=(
                evidence_report.highest_severity
            ),
            triage_records=triage_records,
        )

        # Os motivos e os registros de triagem ficam acessíveis no resumo.
        # A aba "01 - Documentos" também conserva a triagem por documento.
        self._append_triage_to_summary(
            worksheet=summary_sheet,
            records=triage_records,
        )

        workbook.save(
            file_path
        )

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
            "exported_findings": exported_findings,
            "exported_evidences": exported_evidences,
            "exported_financial": exported_financial,
            "exported_financial_reconciliation": exported_financial_reconciliation,
            "exported_prompt_injection": (
                exported_prompt_injection
            ),
            "exported_concealment": (
                exported_concealment
            ),
            "exported_locations": exported_locations,
            "exported_comparisons": exported_comparisons,
            "exported_technical_data": (
                exported_technical_data
            ),
            "exported_images": exported_images,
            "message": (
                "Relatório do lote "
                "exportado com sucesso."
            ),
        }

    def _build_export_view(
        self,
        batch: Batch,
        comparative_findings: list[CrossValidationFinding] | None = None,
        identifier_comparisons: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        analyses: list[dict[str, Any]] = []
        analysis_views: list[dict[str, Any]] = []
        document_analytical_statuses = {}

        for batch_document in batch.documents:
            analysis_id = batch_document.analysis_id

            if analysis_id is None:
                continue

            analysis = self._get_analysis(
                analysis_id
            )

            if analysis is None:
                continue

            analyses.append(analysis)

            analysis_view = (
                self._analysis_view_builder
                .build(analysis)
            )

            analysis_views.append(
                analysis_view
            )

            investigation_cards = (
                self
                ._investigation_view_builder
                .build_cards(
                    analysis_id=analysis_id,
                    analysis_view=analysis_view,
                )
            )

            analytical_status = (
                self._status_resolver
                .resolve(
                    investigation_cards
                )
            )

            document_analytical_statuses[
                str(analysis_id)
            ] = analytical_status

        identifier_observations = []
        for analysis in analyses:
            aid = str(analysis.get("id") or analysis.get("analysis_id") or "")
            filename = str(analysis.get("original_filename") or analysis.get("filename") or "")
            for observation in (analysis.get("document_identifiers") or []):
                if isinstance(observation, dict):
                    identifier_observations.append({
                        **observation, "analysis_id": aid, "filename": filename,
                    })

        finding_summaries = (
            self
            ._finding_aggregation_service
            .aggregate(
                analyses
            )
        )

        return (
            self._export_view_builder
            .build(
                batch=batch,
                finding_summaries=(
                    finding_summaries
                ),
                document_analytical_statuses=(
                    document_analytical_statuses
                ),
                analysis_views=analysis_views,
                comparative_findings=comparative_findings,
                identifier_observations=identifier_observations,
                identifier_comparisons=identifier_comparisons,
            )
        )

    def _build_summary_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
        exported_documents: int,
        exported_findings: int,
        exported_evidences: int,
        exported_financial: int,
        exported_prompt_injection: int,
        exported_concealment: int,
        exported_locations: int,
        exported_comparisons: int,
        exported_technical_data: int,
        exported_images: int,
        highest_severity: EvidenceSeverity | None,
        triage_records: list[dict[str, Any]] | None = None,
        exported_financial_reconciliation: int = 0,
        financial_reconciliations: list[dict[str, Any]] | None = None,
    ) -> None:
        summary = (
            export_view[
                "summary"
            ]
        )

        worksheet.append(
            [
                "Campo",
                "Valor",
            ]
        )

        rows = [
            (
                "ID do lote",
                summary["batch_id"],
            ),
            (
                "Tipo da análise",
                (
                    "Análise de documento individual"
                    if summary["total_documents"] == 1
                    else "Análise em lote"
                ),
            ),
            (
                "Observação",
                (
                    "Esta exportação corresponde à análise de um único "
                    "documento. Indicadores como 1/1 e 100% representam "
                    "a presença do achado neste documento e não um padrão "
                    "comparativo entre documentos."
                    if summary["total_documents"] == 1
                    else (
                        "Esta exportação consolida os resultados dos "
                        "documentos analisados no lote."
                    )
                ),
            ),
            (
                "Status do processamento",
                summary[
                    "processing_status_label"
                ],
            ),
            (
                "Situação analítica",
                summary[
                    "analytical_status_label"
                ],
            ),
            (
                "Criado em",
                summary["created_at"],
            ),
            (
                "Iniciado em",
                summary["started_at"],
            ),
            (
                "Finalizado em",
                summary["finished_at"],
            ),
            (
                "Total de documentos",
                summary[
                    "total_documents"
                ],
            ),
            (
                "Documentos concluídos",
                summary[
                    "completed_documents"
                ],
            ),
            (
                "Documentos com falha",
                summary[
                    "failed_documents"
                ],
            ),
            (
                "Documentos pendentes",
                summary[
                    "pending_documents"
                ],
            ),
            (
                "Documentos em processamento",
                summary[
                    "processing_documents"
                ],
            ),
            (
                "Progresso",
                summary[
                    "progress_label"
                ],
            ),
            (
                "Alta prioridade",
                summary[
                    "alert_documents"
                ],
            ),
            (
                "Revisão recomendada",
                summary[
                    "attention_documents"
                ],
            ),
            (
                "Sem apontamentos",
                summary[
                    "clear_documents"
                ],
            ),
            (
                "Análise incompleta",
                summary[
                    "not_executed_documents"
                ],
            ),
            (
                "Documentos classificados",
                summary[
                    "classified_documents"
                ],
            ),
            (
                "Tipos de achado",
                summary[
                    "finding_type_count"
                ],
            ),
            (
                "Documentos exportados",
                exported_documents,
            ),
            (
                "Achados agregados exportados",
                exported_findings,
            ),
            (
                "Evidências individuais exportadas",
                exported_evidences,
            ),
            (
                "Registros financeiros exportados",
                exported_financial,
            ),
            (
                "Evidências de Prompt Injection exportadas",
                exported_prompt_injection,
            ),
            (
                "Achados de ocultação visual exportados",
                exported_concealment,
            ),
            (
                "Localizações visuais exportadas",
                exported_locations,
            ),
            (
                "Comparações do lote exportadas",
                exported_comparisons,
            ),
            (
                "Registros técnicos exportados",
                exported_technical_data,
            ),
            (
                "Fingerprints de imagem exportados",
                exported_images,
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

        # Indicadores adicionais ficam após o resumo existente,
        # preservando as linhas das versões anteriores.
        triage_records = triage_records or []
        financial_reconciliations = financial_reconciliations or []
        rows.extend([
            (
                "Documentos com sinais que exigem conferência",
                sum(
                    item["triage_priority"] == 1
                    for item in triage_records
                ),
            ),
            (
                "Documentos com ITF repetido no lote",
                sum(
                    "DUPLICATE_ITF" in item["comparative_codes"]
                    for item in triage_records
                ),
            ),
            (
                "Documentos com divergência linha × código",
                sum(
                    item["mismatch_count"] > 0
                    for item in triage_records
                ),
            ),
            (
                "Documentos com registros financeiros inconclusivos",
                sum(
                    item["inconclusive_count"] > 0
                    for item in triage_records
                ),
            ),
            (
                "Critério de triagem",
                "Sinais extraídos; não representa confirmação de fraude "
                "nem altera a classificação individual.",
            ),
            (
                "Documentos com reconciliação financeira disponível",
                len(financial_reconciliations),
            ),
            (
                "Diferenças ITF × Pix observadas (exigem vínculo)",
                sum(
                    item["status"] == "REVIEW_REQUIRED"
                    for item in financial_reconciliations
                ),
            ),
            (
                "Registros de reconciliação exportados",
                exported_financial_reconciliation,
            ),
        ])

        for row in rows:
            worksheet.append(
                row
            )

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        worksheet.column_dimensions[
            "A"
        ].width = 42

        worksheet.column_dimensions[
            "B"
        ].width = 52

        self._style_summary_statuses(
            worksheet=worksheet,
            analytical_status=(
                summary[
                    "analytical_status"
                ]
            ),
        )

    def _build_triage_records(
        self,
        *,
        batch: Batch,
        export_view: dict[str, Any],
        comparative_evidences: list[DocumentEvidence],
        financial_reconciliations: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Prepara uma triagem rastreável usando apenas achados existentes.

        Não promove findings comparativos à classificação individual.
        Candidatos numéricos inconclusivos permanecem inconclusivos.
        """
        relevant_codes = {
            "DUPLICATE_ITF": "Código ITF repetido entre documentos",
            "DUPLICATE_ITF_DIFFERENT_NUMERIC_LINE": (
                "Mesmo ITF com candidatos numéricos diferentes; "
                "confirmar se são linhas digitáveis"
            ),
            "QRCODE_EXACT_MATCH": (
                "QR Code com mesmo conteúdo decodificado e mesmo hash de imagem"
            ),
            "QRCODE_REGENERATED": (
                "Mesmo conteúdo QR com imagens diferentes; causa não determinada"
            ),
            "DOCUMENT_IDENTIFIER_EXACT_MATCH": (
                "Mesmo identificador cadastral observado em outros documentos; "
                "conferir titulares e vínculos contratuais"
            ),
            "DOCUMENT_IDENTIFIER_ONE_DIGIT": (
                "Identificadores cadastrais semelhantes (um dígito); "
                "sem conclusão de adulteração"
            ),
            "DOCUMENT_IDENTIFIER_TRANSPOSITION": (
                "Identificadores cadastrais com transposição adjacente; "
                "requer verificação visual"
            ),
        }
        ids_to_analysis: dict[str, str] = {}
        unique_names: dict[str, str | None] = {}
        for document in batch.documents:
            analysis_id = (
                str(document.analysis_id)
                if document.analysis_id is not None else ""
            )
            ids_to_analysis[str(document.document_id)] = analysis_id
            if analysis_id:
                ids_to_analysis[analysis_id] = analysis_id
            name = document.original_filename
            if name in unique_names:
                unique_names[name] = None
            else:
                unique_names[name] = analysis_id

        codes_by_analysis: dict[str, set[str]] = {}
        for evidence in comparative_evidences:
            code = str(evidence.code)
            if code not in relevant_codes:
                continue
            metadata = dict(evidence.metadata or {})
            participants: set[str] = set()

            for identifier in evidence.document_ids:
                match = ids_to_analysis.get(str(identifier))
                if match:
                    participants.add(match)

            # Nomes duplicados são ambíguos e não são usados para vínculo.
            for name in self._extract_comparison_document_names(metadata):
                analysis_id = unique_names.get(name)
                if analysis_id:
                    participants.add(analysis_id)

            for analysis_id in participants:
                codes_by_analysis.setdefault(analysis_id, set()).add(code)

        # Comparações observacionais, não adicionadas ao score individual.
        identifier_matches_by_analysis: dict[str, list[dict[str, Any]]] = {}
        for comparison in export_view.get("identifier_comparisons", []):
            if not isinstance(comparison, dict):
                continue
            code = str(comparison.get("code") or "")
            if code not in relevant_codes:
                continue
            for participant in comparison.get("participants", []) or []:
                analysis_id = str(participant.get("analysis_id") or "")
                if analysis_id and analysis_id in ids_to_analysis:
                    identifier_matches_by_analysis.setdefault(analysis_id, []).append(comparison)
                    codes_by_analysis.setdefault(analysis_id, set()).add(code)

        reconciliations_by_id = {
            item["analysis_id"]: item
            for item in (financial_reconciliations or [])
            if item.get("analysis_id")
        }

        financial_by_analysis: dict[str, dict[str, int]] = {}
        for item in export_view.get("financial", []):
            analysis_id = str(item.get("analysis_id") or "")
            if not analysis_id:
                continue
            counters = financial_by_analysis.setdefault(
                analysis_id,
                {"invalid": 0, "mismatch": 0, "inconclusive": 0},
            )
            status = str(item.get("status") or "").lower().strip()
            record_type = item.get("record_type")
            if record_type == "validation" and status == "invalid":
                counters["invalid"] += 1
            elif record_type == "comparison" and status == "mismatch":
                counters["mismatch"] += 1
            elif status in ("inconclusive", "not_applicable"):
                counters["inconclusive"] += 1

        export_documents = {
            str(item.get("analysis_id")): item
            for item in export_view.get("documents", [])
            if item.get("analysis_id")
        }

        result: list[dict[str, Any]] = []
        for document in batch.documents:
            analysis_id = str(document.analysis_id) if document.analysis_id else ""
            exported = export_documents.get(analysis_id, {})
            counts = financial_by_analysis.get(analysis_id, {})
            invalid_count = counts.get("invalid", 0)
            mismatch_count = counts.get("mismatch", 0)
            inconclusive_count = counts.get("inconclusive", 0)
            codes = sorted(codes_by_analysis.get(analysis_id, set()))
            reasons = [relevant_codes[code] for code in codes]
            contextual_count = sum(
                str(f.get("analysis_id") or "") == analysis_id
                for f in export_view.get("contextual_payment_line_findings", [])
            )
            if contextual_count:
                reasons.append(
                    f"{contextual_count} achado(s) contextual(is) de estrutura inválida "
                    "em linha de pagamento (ver 03 - Evidências). Este achado "
                    "não equivale ao status INVALID do validador estrito; "
                    "a contagem de validações inválidas considera apenas esse status."
                )
            observed_kinds = {
                item.get("kind") for item in export_view.get("identifier_observations", [])
                if str(item.get("analysis_id") or "") == analysis_id and item.get("value")
            }
            if observed_kinds:
                missing_labels = [
                    label for kind, label in DocumentIdentifierService.LABELS.items()
                    if kind not in observed_kinds
                ]
                if missing_labels:
                    reasons.append(
                        "Campos não identificados nesta extração: " + ", ".join(missing_labels)
                        + ". Ausência de leitura não confirma ausência no documento."
                    )
            matching = identifier_matches_by_analysis.get(analysis_id, [])
            if matching:
                names = sorted({str(f.get("label") or "") for f in matching})
                reasons.append(
                    f"{len(matching)} coincidência(s) de campo(s) cadastrais: "
                    f"{', '.join(names)} (ver 08 - Comparações; verificação humana pendente)"
                )
            reconciled = reconciliations_by_id.get(analysis_id, {})
            reconciliation_status = reconciled.get("status")
            if reconciliation_status == "REVIEW_REQUIRED":
                reasons.append(
                    "Diferença observada entre valores ITF e Pix na mesma "
                    "página; vínculo entre os meios de pagamento e a mesma "
                    "cobrança ainda não confirmado "
                    f"(ver {self.FINANCIAL_RECONCILIATION_SHEET_NAME})"
                )
            elif reconciliation_status == "INCONCLUSIVE" and reconciled.get("issues"):
                reasons.append(
                    "Reconciliação financeira inconclusiva, com limitações "
                    f"registradas (ver {self.FINANCIAL_RECONCILIATION_SHEET_NAME})"
                )
            if invalid_count:
                reasons.append(
                    f"{invalid_count} candidato(s) numérico(s) "
                    "com validação estrutural inválida"
                )
            if mismatch_count:
                reasons.append(
                    f"{mismatch_count} comparação(ões) linha × código "
                    "com divergência sinalizada"
                )
            if inconclusive_count:
                reasons.append(
                    f"{inconclusive_count} registro(s) financeiro(s) "
                    "inconclusivo(s), sem confirmação de divergência"
                )

            if not analysis_id or not exported:
                priority = 4
                label = "Sem resultado individual disponível"
            elif mismatch_count or invalid_count or contextual_count or (
                "DUPLICATE_ITF_DIFFERENT_NUMERIC_LINE" in codes
            ):
                priority = 1
                label = "Revisar inconsistências sinalizadas"
            elif reconciliation_status == "REVIEW_REQUIRED":
                priority = 2
                label = "Conferir diferença entre valores codificados"
            elif codes:
                priority = 2
                label = "Conferir comparação entre documentos"
            elif inconclusive_count:
                priority = 3
                label = "Conferir extração / dados inconclusivos"
            else:
                priority = 5
                label = "Sem sinal específico nesta triagem"

            result.append({
                "filename": document.original_filename,
                "analysis_id": analysis_id,
                "analytical_status_label": exported.get(
                    "analytical_status_label", "Análise incompleta"
                ),
                "comparative_count": (
                    (exported.get("comparative_finding_count", 0) or 0)
                    + len(identifier_matches_by_analysis.get(analysis_id, []))
                ),
                "comparative_severity": (
                    exported.get("comparative_highest_severity_label")
                    or ("Informativo (identificadores)"
                        if identifier_matches_by_analysis.get(analysis_id) else None)
                ),
                "comparative_codes": codes,
                "invalid_count": invalid_count,
                "contextual_invalid_count": contextual_count,
                "mismatch_count": mismatch_count,
                "inconclusive_count": inconclusive_count,
                "triage_priority": priority,
                "triage_label": label,
                "reasons": "\n".join(reasons),
            })

        # A ordem destaca inconsistências sem modificar prioridades formais.
        return sorted(result, key=lambda item: (
            item["triage_priority"], item["filename"]
        ))

    def _append_triage_to_summary(
        self,
        *,
        worksheet,
        records: list[dict[str, Any]],
    ) -> None:
        """Insere a triagem no 00 - Resumo, mantendo status individual intacto."""
        worksheet.append([])
        title_row = worksheet.max_row + 1
        worksheet.append(["TRIAGEM TÉCNICA POR DOCUMENTO — não altera status individual"])
        worksheet.merge_cells(
            start_row=title_row, start_column=1,
            end_row=title_row, end_column=12,
        )
        title_cell = worksheet.cell(row=title_row, column=1)
        title_cell.fill = PatternFill(fill_type="solid", fgColor="24184F")
        title_cell.font = Font(color="FFFFFF", bold=True)
        title_cell.alignment = Alignment(vertical="center")
        worksheet.row_dimensions[title_row].height = 24

        worksheet.append([
            "Documento", "Situação individual", "Triagem técnica",
            "Motivos para revisão / limitações", "Códigos comparativos",
            "Total de comparações", "Severidade comparativa",
            "Validações inválidas", "Divergências linha × código",
            "Registros inconclusivos", "Ver comparações", "ID da análise",
        ])
        header_row = worksheet.max_row
        for cell in worksheet[header_row]:
            cell.fill = PatternFill(fill_type="solid", fgColor="29366B")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        worksheet.row_dimensions[header_row].height = 32

        for item in records:
            worksheet.append([
                item["filename"],
                item["analytical_status_label"],
                item["triage_label"],
                item["reasons"],
                self._join_values(item["comparative_codes"]),
                item["comparative_count"],
                item["comparative_severity"],
                item["invalid_count"],
                item["mismatch_count"],
                item["inconclusive_count"],
                self.COMPARISONS_SHEET_NAME if item["comparative_count"] else None,
                item["analysis_id"],
            ])
        self._set_column_widths(
            worksheet, [42, 52, 38, 70, 42, 22, 25, 22, 24, 22, 22, 38],
        )
        if records:
            table = Table(
                displayName="DocDNA_TriagemResumo",
                ref=f"A{header_row}:L{worksheet.max_row}",
            )
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2", showFirstColumn=False,
                showLastColumn=False, showRowStripes=True,
                showColumnStripes=False,
            )
            worksheet.add_table(table)

    def _build_triage_sheet(
        self,
        *,
        worksheet,
        records: list[dict[str, Any]],
    ) -> None:
        """Exibe um índice revisável dos sinais já existentes no lote."""
        headers = [
            "Documento",
            "Situação individual",
            "Triagem técnica (não altera status)",
            "Motivos para revisão / limitações",
            "Códigos comparativos relevantes",
            "Total de findings comparativos",
            "Maior severidade comparativa",
            "Validações numéricas inválidas",
            "Divergências linha × código",
            "Registros financeiros inconclusivos",
            "Referência às comparações",
            "ID da análise",
        ]
        worksheet.append(headers)
        for item in records:
            worksheet.append([
                item["filename"],
                item["analytical_status_label"],
                item["triage_label"],
                item["reasons"],
                self._join_values(item["comparative_codes"]),
                item["comparative_count"],
                item["comparative_severity"],
                item["invalid_count"],
                item["mismatch_count"],
                item["inconclusive_count"],
                self.COMPARISONS_SHEET_NAME if item["comparative_count"] else None,
                item["analysis_id"],
            ])
        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="D2",
            auto_filter=False,
        )
        self._set_column_widths(
            worksheet,
            [38, 22, 39, 72, 42, 22, 24, 23, 23, 23, 24, 38],
        )
        # A cor é auxílio visual de triagem, não severidade forense.
        triage_colors = {
            1: ("FCE8EC", "9F1239"),
            2: ("FFF4D6", "92400E"),
            3: ("EAF1FC", "1D4ED8"),
            4: ("EEF2F6", "475569"),
        }
        for row_index, item in enumerate(records, start=2):
            colors = triage_colors.get(item["triage_priority"])
            if not colors:
                continue
            status_cell = worksheet.cell(row=row_index, column=3)
            status_cell.fill = PatternFill(
                fill_type="solid", fgColor=colors[0]
            )
            status_cell.font = Font(
                color=colors[1], bold=True
            )
        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_Triagem",
        )

    def _build_documents_sheet(
        self,
        worksheet,
        batch: Batch,
        export_view: dict[str, Any],
        triage_by_analysis_id: dict[str, dict[str, Any]] | None = None,
    ) -> int:
        triage_by_analysis_id = triage_by_analysis_id or {}
        documents_by_analysis_id = {
            str(document["analysis_id"]): document
            for document in export_view["documents"]
            if document["analysis_id"]
        }
        # Inclui os vínculos observacionais na navegação do Excel,
        # mas nunca altera a classificação individual (CLEAR/ATTENTION/ALERT).
        identifier_matches_by_id: dict[str, list[dict[str, Any]]] = {}
        for item in export_view.get("identifier_comparisons", []):
            if not isinstance(item, dict):
                continue
            for participant in item.get("participants", []) or []:
                if not isinstance(participant, dict):
                    continue
                aid = str(participant.get("analysis_id") or "")
                if aid:
                    identifier_matches_by_id.setdefault(aid, []).append(item)

        headers = [
            "Documento",
            "Status no lote",
            "Situação analítica",
            "Código analítico",
            "Possui apontamentos comparativos",
            "Quantidade de apontamentos comparativos",
            "Maior severidade comparativa",
            "Referência comparativa",
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
            "Triagem técnica (não altera status individual)",
            "Motivos para revisão / limitações",
            "Códigos comparativos relevantes",
            "Validações numéricas inválidas",
            "Divergências linha × código",
            "Registros financeiros inconclusivos",
            "Conta identificada", "Cliente identificado", "Fatura identificada",
            "Débito automático identificado", "Titular informado",
        ]

        worksheet.append(headers)

        exported_documents = 0
        identifier_by_id: dict[str, dict[str, list[str]]] = {}
        for item in export_view.get("identifier_observations", []):
            if not isinstance(item, dict):
                continue
            aid = str(item.get("analysis_id") or "")
            kind = str(item.get("kind") or "")
            if aid and kind:
                identifier_by_id.setdefault(aid, {}).setdefault(kind, []).append(
                    str(item.get("value") or "")
                )

        for batch_document in batch.documents:
            analysis_id_key = (
                str(batch_document.analysis_id)
                if batch_document.analysis_id
                else ""
            )

            exported_document = documents_by_analysis_id.get(
                analysis_id_key
            )

            analytical_status = (
                exported_document["analytical_status"]
                if exported_document
                else "not_executed"
            )

            analytical_status_label = (
                exported_document["analytical_status_label"]
                if exported_document
                else "Análise incompleta"
            )

            # A situação individual continua independente dos achados de lote.
            has_comparative_findings = bool(
                exported_document.get("has_comparative_findings", False)
                if exported_document
                else False
            )
            comparative_finding_count = (
                exported_document.get("comparative_finding_count", 0) or 0
                if exported_document
                else 0
            )
            comparative_highest_severity_label = (
                exported_document.get("comparative_highest_severity_label")
                if exported_document
                else None
            )
            observed_matches = identifier_matches_by_id.get(analysis_id_key, [])
            if observed_matches:
                has_comparative_findings = True
                comparative_finding_count += len(observed_matches)
                if not comparative_highest_severity_label:
                    comparative_highest_severity_label = (
                        "Revisão recomendada (observacional)"
                        if any(i.get("severity") == "Revisão recomendada"
                               for i in observed_matches)
                        else "Informativo (observacional)"
                    )

            comparative_columns = [
                "Sim" if has_comparative_findings else "Não",
                comparative_finding_count,
                (
                    comparative_highest_severity_label or "Não informada"
                    if has_comparative_findings
                    else None
                ),
                (
                    self.COMPARISONS_SHEET_NAME
                    if has_comparative_findings
                    else None
                ),
            ]

            triage = triage_by_analysis_id.get(analysis_id_key, {})
            triage_columns = [
                triage.get("triage_label", "Não avaliada nesta triagem"),
                triage.get("reasons", ""),
                self._join_values(triage.get("comparative_codes", [])),
                triage.get("invalid_count", 0),
                triage.get("mismatch_count", 0),
                triage.get("inconclusive_count", 0),
            ]

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
                        analytical_status_label,
                        analytical_status,
                        *comparative_columns,
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
                        *triage_columns,
                        None, None, None, None, None,
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
                    analytical_status_label,
                    analytical_status,
                    *comparative_columns,
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
                    *triage_columns,
                    *[
                        self._safe_financial_excel_text(" | ".join(dict.fromkeys(
                            identifier_by_id.get(analysis_id_key, {}).get(kind, [])
                        )))
                        for kind in ("account", "customer", "invoice",
                                     "automatic_debit", "holder")
                    ],
                ]
            )

            exported_documents += 1

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_documents_column_widths(
            worksheet
        )
        for index in range(len(headers) - 4, len(headers) + 1):
            worksheet.column_dimensions[get_column_letter(index)].width = 32

        self._style_document_statuses(
            worksheet
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_Documentos",
        )

        return exported_documents

    def _build_findings_sheet(
            self,
            worksheet,
            export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Código",
            "Tipo de achado",
            "Documentos afetados",
            "Total de documentos",
            "Prevalência",
            "Ocorrências",
            "Maior confiança",
            "IDs das análises afetadas",
        ]

        worksheet.append(
            headers
        )

        findings = (
            export_view[
                "findings_by_type"
            ]
        )

        if not findings:
            worksheet.append(
                [
                    "SEM_ACHADOS",
                    (
                        "Nenhum achado "
                        "agregado identificado"
                    ),
                    0,
                    export_view[
                        "summary"
                    ][
                        "total_documents"
                    ],
                    0.0,
                    0,
                    0.0,
                    "",
                ]
            )
        else:
            for finding in findings:
                worksheet.append(
                    [
                        finding["code"],
                        finding["title"],
                        finding[
                            "affected_documents"
                        ],
                        finding[
                            "total_documents"
                        ],
                        finding[
                            "prevalence_ratio"
                        ],
                        finding[
                            "occurrence_count"
                        ],
                        finding[
                            "highest_confidence"
                        ],
                        self._join_values(
                            finding[
                                "affected_document_ids"
                            ]
                        ),
                    ]
                )

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        for cell in worksheet["E"][1:]:
            cell.number_format = (
                "0.0%"
            )

        for cell in worksheet["G"][1:]:
            cell.number_format = (
                "0%"
            )

        widths = {
            "A": 32,
            "B": 38,
            "C": 22,
            "D": 22,
            "E": 18,
            "F": 18,
            "G": 18,
            "H": 70,
        }

        for column, width in (
                widths.items()
        ):
            worksheet.column_dimensions[
                column
            ].width = width

        self._add_excel_table(
            worksheet=worksheet,
            table_name=(
                "DocDNA_AchadosPorTipo"
            ),
        )

        return len(findings)

    def _build_evidences_sheet(
        self,
        worksheet,
        batch: Batch,
    ) -> int:
        """Exporta achados persistidos e leituras técnicas sem confundi-los.

        Uma leitura de código é uma OBSERVAÇÃO, não evidência de fraude.
        O retorno contabiliza somente as evidências originais do detector.
        """
        headers = [
            "Documento", "ID da análise", "Código da evidência",
            "Título", "Descrição", "Severidade", "Detector", "Confiança",
            "Natureza do registro", "Simbologia", "Conteúdo decodificado",
            "Comprimento", "Página", "Condição técnica",
        ]
        worksheet.append(headers)
        exported_evidences = 0
        barcode_observations = 0

        for batch_document in batch.documents:
            analysis = self._get_analysis(batch_document.analysis_id)
            if not isinstance(analysis, dict):
                continue

            filename = batch_document.original_filename
            analysis_id = self._optional_uuid(batch_document.analysis_id)
            for evidence in analysis.get("evidences", []) or []:
                severity = self._enum_value(
                    self._safe_attribute(evidence, "severity")
                )
                confidence = self._safe_attribute(evidence, "confidence")
                worksheet.append([
                    filename,
                    analysis_id,
                    self._safe_attribute(evidence, "code"),
                    self._safe_attribute(evidence, "title"),
                    self._safe_attribute(evidence, "description"),
                    self._translate_severity_value(severity),
                    (
                        self._safe_attribute(evidence, "detector")
                        or self._safe_attribute(evidence, "source")
                    ),
                    self._format_confidence(confidence),
                    "Achado original do detector",
                    None, None, None, None, None,
                ])
                exported_evidences += 1

            for barcode in analysis.get("barcodes", []) or []:
                content = str(self._safe_attribute(barcode, "content") or "")
                if not content:
                    continue
                format_name = str(self._safe_attribute(barcode, "format") or "Não informado")
                page = self._safe_attribute(barcode, "page_number")
                condition = self._barcode_reading_condition(format_name, content)
                worksheet.append([
                    filename,
                    analysis_id,
                    "BARCODE_READ_OBSERVED",
                    "Código decodificado — observação técnica",
                    (
                        f"Conteúdo efetivamente lido: {content[:1000]}. "
                        "Esta leitura não comprova pagamento, valor ou autenticidade. "
                        f"{condition}"
                    ),
                    "Informativo",
                    "BarcodeReader (resultado armazenado)",
                    None,
                    "Leitura técnica, NÃO é novo indício de fraude",
                    format_name,
                    self._safe_financial_excel_text(content),
                    len(content),
                    page if type(page) is int else None,
                    condition,
                ])
                barcode_observations += 1

        identifier_observations = 0
        for item in self._current_identifier_observations:
            if not isinstance(item, dict):
                continue
            value = self._safe_financial_excel_text(item.get("value"))
            page = item.get("page_number")
            source = self._safe_financial_excel_text(item.get("source"))
            worksheet.append([
                self._safe_financial_excel_text(item.get("filename")),
                self._safe_financial_excel_text(item.get("analysis_id")),
                "DOCUMENT_IDENTIFIER_OBSERVED",
                self._safe_financial_excel_text(item.get("label")),
                f"{item.get('label')}: {value}. Fonte: {source}. "
                "Leitura observacional, ainda sujeita à confirmação. "
                + (str(item.get("review_reason")) + " Leituras alternativas: "
                   + ", ".join(str(r.get("value")) for r in item.get("alternative_readings", []))
                   if item.get("reading_conflict") else ""),
                "Informativo", "DocumentIdentifierService",
                item.get("confidence"),
                "Campo documental identificado (observacional, não comprova fraude)",
                None, value,
                len(value), page if type(page) is int else None,
                "Campo identificado por rótulo; verificar OCR e documento",
            ])
            identifier_observations += 1

        if exported_evidences == 0 and barcode_observations == 0 and identifier_observations == 0:
            worksheet.append([
                "Nenhuma evidência ou leitura de código foi registrada."
            ] + [None] * (len(headers) - 1))

        self._style_worksheet(
            worksheet=worksheet, freeze_panes="C2", auto_filter=False,
        )
        self._set_column_widths(
            worksheet,
            [38, 38, 32, 44, 78, 18, 40, 16, 45, 22, 74, 16, 12, 68],
        )
        self._add_excel_table(
            worksheet=worksheet, table_name="DocDNA_Evidencias",
        )
        return exported_evidences

    def _build_financial_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
        batch: Batch | None = None,
        reconciliation_records: list[dict[str, Any]] | None = None,
    ) -> int:
        """Visão financeira única: validações + códigos lidos + reconciliação.

        Não reabre PDFs, não refaz cálculos e não confunde uma leitura
        de barras com um pagamento validado.
        """
        headers = [
            "Documento", "ID da análise", "Tipo de registro",
            "Índice da linha", "Índice do barcode", "Linha digitável",
            "Tipo da linha", "Status", "Método de validação",
            "DVs válidos", "Total de DVs", "Barcode calculado",
            "Barcode detectado", "Mensagem",
            "Simbologia da leitura", "Conteúdo bruto do código",
            "Comprimento do conteúdo", "Página do código",
            "Condição técnica da leitura", "Fonte do valor",
            "Valor em BRL (observado)", "Proveniência técnica",
            "SHA-256 do conteúdo", "Limitações / observações",
            "Posição X (PDF)", "Posição Y (PDF)",
            "Largura (PDF)", "Altura (PDF)",
        ]
        worksheet.append(headers)
        records = export_view.get("financial", []) or []

        for record in records:
            worksheet.append([
                record.get("filename"),
                record.get("analysis_id"),
                record.get("record_type_label"),
                record.get("line_index"),
                record.get("barcode_index"),
                record.get("numeric_line"),
                record.get("line_type_label"),
                record.get("status_label"),
                record.get("validation_method_label"),
                record.get("valid_check_digits"),
                record.get("total_check_digits"),
                record.get("converted_barcode"),
                record.get("detected_barcode"),
                record.get("message"),
            ] + [None] * (len(headers) - 14))

        # Cada código decodificado é visível mesmo quando não existe
        # linha de arrecadação de 44 dígitos nem reconciliação financeira.
        if batch is not None:
            for document in batch.documents:
                analysis = self._get_analysis(document.analysis_id)
                if not isinstance(analysis, dict):
                    continue
                for ordinal, barcode in enumerate(
                    analysis.get("barcodes", []) or [], start=1
                ):
                    content = str(self._safe_attribute(barcode, "content") or "")
                    if not content:
                        continue
                    fmt = str(self._safe_attribute(barcode, "format") or "Não informado")
                    barcode_index = self._safe_attribute(barcode, "barcode_index")
                    page_number = self._safe_attribute(barcode, "page_number")
                    condition = self._barcode_reading_condition(fmt, content)
                    box = self._safe_attribute(
                        self._safe_attribute(barcode, "location"), "bounding_box"
                    )
                    row = [None] * len(headers)
                    row[0] = document.original_filename
                    row[1] = self._optional_uuid(document.analysis_id)
                    row[2] = "Código decodificado (observação)"
                    row[4] = barcode_index if type(barcode_index) is int else ordinal
                    row[7] = "Informativo — leitura técnica"
                    row[12] = self._safe_financial_excel_text(content)
                    row[13] = condition
                    row[14] = fmt
                    row[15] = self._safe_financial_excel_text(content)
                    row[16] = len(content)
                    row[17] = page_number if type(page_number) is int else None
                    row[18] = condition
                    row[22] = sha256(content.encode("utf-8")).hexdigest()
                    row[23] = (
                        "Leitura isolada não comprova valor, pagamento, "
                        "titularidade nem autenticidade."
                    )
                    for position, field in enumerate(
                        ("x", "y", "width", "height"), start=24
                    ):
                        value = self._safe_attribute(box, field)
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            row[position] = value
                    worksheet.append(row)

        status_labels = {
            "REVIEW_REQUIRED": "Conferir diferença observada (vínculo pendente)",
            "CONSISTENT": "Valores codificados iguais (não atesta autenticidade)",
            "INCONCLUSIVE": "Inconclusivo",
            "UNKNOWN": "Status não reconhecido",
        }
        for entry in reconciliation_records or []:
            filename = self._safe_financial_excel_text(entry.get("filename"))
            analysis_id = self._safe_financial_excel_text(entry.get("analysis_id"))
            status = entry.get("status", "UNKNOWN")
            issues = " | ".join(str(x) for x in entry.get("issues", []))
            row = [None] * len(headers)
            row[0] = filename
            row[1] = analysis_id
            row[2] = "Reconciliação — resumo"
            row[7] = status_labels.get(status, status)
            row[13] = self._safe_financial_excel_text(entry.get("message"))
            row[23] = self._safe_financial_excel_text(issues)
            worksheet.append(row)

            for value in entry.get("values", []):
                raw = str(value.get("raw_content") or "")
                row = [None] * len(headers)
                row[0] = filename
                row[1] = analysis_id
                row[2] = "Reconciliação — valor observado"
                index = value.get("barcode_index")
                row[4] = index if type(index) is int else None
                row[7] = "Valor observado (vínculo conforme resumo)"
                row[15] = self._safe_financial_excel_text(raw, maximum_length=2000)
                row[16] = len(raw) if raw else None
                page = value.get("page_number")
                row[17] = page if type(page) is int else None
                row[19] = self._safe_financial_excel_text(value.get("source"), maximum_length=60)
                row[20] = self._safe_financial_excel_text(value.get("amount"), maximum_length=60)
                row[21] = self._safe_financial_excel_text(value.get("provenance"), maximum_length=120)
                row[22] = sha256(raw.encode("utf-8")).hexdigest() if raw else None
                worksheet.append(row)

        if worksheet.max_row == 1:
            worksheet.append([
                "Nenhum registro financeiro nem código decodificado foi armazenado."
            ] + [None] * (len(headers) - 1))

        self._style_worksheet(
            worksheet=worksheet, freeze_panes="C2", auto_filter=False,
        )
        self._set_column_widths(worksheet, [
            38, 38, 34, 16, 18, 64, 28, 44, 26, 14, 14,
            60, 70, 76, 23, 74, 19, 16, 70, 22, 22,
            44, 65, 68, 20, 20, 22, 22,
        ])
        self._add_excel_table(
            worksheet=worksheet, table_name="DocDNA_Financeiro",
        )
        return len(records)

    @staticmethod
    def _barcode_reading_condition(format_name: str, content: str) -> str:
        """Comunica limites de uma leitura; não reclassifica achados."""
        normalized = re.sub(r"[^a-z0-9]", "", str(format_name).lower())
        if "itf" in normalized or "interleaved" in normalized:
            if len(content) == 44 and content.isascii() and content.isdigit():
                return (
                    "ITF de 44 dígitos: comprimento compatível com código "
                    "de arrecadação; estrutura e vínculo ainda requerem validação."
                )
            return (
                f"ITF de {len(content)} caracteres: não é um código "
                "de arrecadação completo de 44 dígitos."
            )
        if "qr" in normalized:
            return (
                "QR Code decodificado; não se presume validade de "
                "cobrança Pix nem correspondência com ITF."
            )
        return (
            "Código decodificado; simbologia/conteúdo não confirmam "
            "instrumento de pagamento."
        )

    def _build_financial_reconciliation_records(
        self,
        batch: Batch,
    ) -> list[dict[str, Any]]:
        """Consulta resultados armazenados; nunca reexecuta reconciliação.

        Um lote anterior à feature pode não ter a chave de reconciliação.
        Nesses casos não inventamos um INCONCLUSIVE ou um valor monetário.
        """
        records: list[dict[str, Any]] = []
        for document in batch.documents:
            if document.analysis_id is None:
                continue
            analysis = self._get_analysis(document.analysis_id)
            if not isinstance(analysis, dict):
                continue
            reconciliation = analysis.get("financial_reconciliation")
            if not isinstance(reconciliation, dict):
                continue

            raw_status = str(reconciliation.get("status") or "").upper()
            status = (
                raw_status if raw_status in {
                    "REVIEW_REQUIRED", "CONSISTENT", "INCONCLUSIVE"
                } else "UNKNOWN"
            )
            raw_values = reconciliation.get("values")
            values = (
                [value for value in raw_values if isinstance(value, dict)]
                if isinstance(raw_values, list) else []
            )
            raw_issues = reconciliation.get("issues")
            issues = (
                list(raw_issues) if isinstance(raw_issues, list) else []
            )
            records.append({
                "filename": str(document.original_filename or ""),
                "analysis_id": str(document.analysis_id),
                "status": status,
                "message": str(reconciliation.get("message") or ""),
                "issues": issues,
                "values": values,
            })
        return records

    @staticmethod
    def _safe_financial_excel_text(
        value: Any,
        *,
        maximum_length: int = 2000,
    ) -> str:
        """Evita fórmulas injetadas e textos que excedam limites do XLSX.

        Aplica-se só aos novos campos; os dados originais permanecem intactos
        no repositório e o SHA-256 da evidência é calculado sem truncamento.
        """
        normalized = str(value if value is not None else "")
        normalized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", normalized)
        normalized = normalized[:maximum_length]
        if normalized.lstrip().startswith(("=", "+", "-", "@")):
            normalized = "'" + normalized
        return normalized

    def _build_financial_reconciliation_sheet(
        self,
        *,
        worksheet,
        records: list[dict[str, Any]],
    ) -> int:
        """Exibe cada observação e o diagnóstico *observacional* da análise.

        REVIEW_REQUIRED não significa fraude, divergência comprovada da
        mesma cobrança ou mudança automática na situação individual.
        """
        headers = [
            "Documento", "ID da análise", "Tipo de registro",
            "Status consolidado (não é fraude)", "Fonte", "Valor em BRL",
            "Página", "Índice do código", "Proveniência técnica",
            "Trecho do conteúdo original", "SHA-256 do conteúdo original",
            "Mensagem técnica", "Limitações da interpretação",
        ]
        worksheet.append(headers)
        written = 0
        status_labels = {
            "REVIEW_REQUIRED": "Conferir diferença observada (vínculo pendente)",
            "CONSISTENT": "Valores codificados iguais (não atesta autenticidade)",
            "INCONCLUSIVE": "Inconclusivo",
            "UNKNOWN": "Status não reconhecido",
        }
        for entry in records:
            filename = self._safe_financial_excel_text(entry["filename"])
            analysis_id = self._safe_financial_excel_text(entry["analysis_id"])
            status = entry.get("status", "UNKNOWN")
            issues = " | ".join(str(x) for x in entry.get("issues", []))
            # Linha consolidada mesmo quando nenhum valor pôde ser interpretado.
            worksheet.append([
                filename, analysis_id, "Resumo", status_labels.get(status, status),
                None, None, None, None, None, None, None,
                self._safe_financial_excel_text(entry.get("message"), maximum_length=2000),
                self._safe_financial_excel_text(issues, maximum_length=2000),
            ])
            written += 1
            for value in entry.get("values", []):
                raw = str(value.get("raw_content") or "")
                # SHA refere-se ao conteúdo da observação, NÃO ao PDF inteiro.
                content_hash = sha256(raw.encode("utf-8")).hexdigest() if raw else None
                worksheet.append([
                    filename, analysis_id, "Valor observado", None,
                    self._safe_financial_excel_text(value.get("source"), maximum_length=60),
                    self._safe_financial_excel_text(value.get("amount"), maximum_length=60),
                    value.get("page_number") if type(value.get("page_number")) is int else None,
                    value.get("barcode_index") if type(value.get("barcode_index")) is int else None,
                    self._safe_financial_excel_text(value.get("provenance"), maximum_length=120),
                    self._safe_financial_excel_text(raw, maximum_length=512),
                    content_hash, None, None,
                ])
                written += 1

        if not records:
            worksheet.append([
                "Reconciliação não disponível nas análises deste lote.",
                None, "Sem dados", None,
            ] + [None] * (len(headers) - 4))

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="D2",
            auto_filter=False,
        )
        self._set_column_widths(
            worksheet,
            [38, 38, 22, 48, 18, 20, 12, 18, 42, 72, 65, 76, 76],
        )
        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_ReconciliacaoFinanceira",
        )
        return written

    def _build_prompt_injection_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Índice da evidência",
            "Risco",
            "Score da análise",
            "Código",
            "Categoria",
            "Detector",
            "Página",
            "Origem",
            "Confiança",
            "Peso",
            "Score ponderado",
            "Regra identificada",
            "Trecho original",
            "Trecho normalizado",
            "Idioma",
            "Fonte",
            "Tamanho da fonte",
            "Cor da fonte",
            "Maior fonte da página",
            "Método de análise",
            "Grupos de sinais",
            "Sinais identificados",
            "Descrição",
        ]

        worksheet.append(headers)

        records = export_view.get(
            "prompt_injection",
            [],
        )

        if not records:
            worksheet.append(
                [
                    "Nenhum apontamento de Prompt Injection foi identificado.",
                ]
                + [None] * (len(headers) - 1)
            )

        for record in records:
            worksheet.append(
                [
                    record.get("filename"),
                    record.get("analysis_id"),
                    record.get("evidence_index"),
                    record.get("risk_label"),
                    self._ratio_value(record.get("score")),
                    record.get("code"),
                    record.get("category_label"),
                    record.get("detector"),
                    record.get("page_number"),
                    record.get("source_label"),
                    self._ratio_value(record.get("confidence")),
                    self._ratio_value(record.get("weight")),
                    self._ratio_value(record.get("weighted_score")),
                    record.get("matched_rule"),
                    record.get("original_excerpt"),
                    record.get("normalized_excerpt"),
                    record.get("language"),
                    record.get("font_name"),
                    record.get("font_size"),
                    record.get("font_color"),
                    record.get("maximum_font_size"),
                    record.get("analysis_method"),
                    self._join_values(
                        record.get("signal_groups", [])
                    ),
                    self._format_json_value(
                        record.get("matched_signals")
                    ),
                    record.get("description"),
                ]
            )

        for column in ("E", "K", "L", "M"):
            for cell in worksheet[column][1:]:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "0.0%"

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_column_widths(
            worksheet,
            [
                38, 38, 18, 18, 18, 34, 32, 42,
                12, 24, 16, 14, 18, 48, 80, 80,
                14, 28, 18, 20, 20, 24, 40, 58, 70,
            ],
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_PromptInjection",
        )

        return len(records)

    def _build_concealment_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Índice do finding",
            "Tipo",
            "Código",
            "Detector",
            "Página",
            "Texto",
            "Descrição",
            "Fonte",
            "Tamanho da fonte",
            "Cor da fonte",
            "Cor estimada do fundo",
            "Luminância relativa da fonte",
            "Luminância relativa do fundo",
            "Razão de contraste",
            "Limiar de contraste",
            "Classificação de contraste",
            "Predominância do fundo",
            "Método de amostragem",
            "Referência da métrica",
            "Confiança",
            "Sinais técnicos",
            "Texto branco/quase branco",
            "Baixo contraste",
            "Contraste extremamente baixo",
            "Texto pequeno",
            "Pequeno relativo à página",
            "Conteúdo instrucional",
            "Coordenadas",
            "Localizado visualmente",
            "Imagem de origem",
            "Imagem anotada",
        ]

        worksheet.append(headers)

        records = export_view.get(
            "concealment",
            [],
        )

        if not records:
            worksheet.append(
                [
                    "Nenhum achado de ocultação visual foi identificado.",
                ]
                + [None] * (len(headers) - 1)
            )

        for record in records:
            signal_labels = record.get(
                "signal_labels",
                [],
            )

            if not signal_labels:
                signal_labels = record.get(
                    "signals",
                    [],
                )

            worksheet.append(
                [
                    record.get("filename"),
                    record.get("analysis_id"),
                    record.get("finding_index"),
                    record.get("concealment_type_label"),
                    record.get("code"),
                    record.get("detector"),
                    record.get("page_number"),
                    record.get("text"),
                    record.get("description"),
                    record.get("font_name"),
                    record.get("font_size"),
                    record.get("font_color_hex"),
                    record.get("background_color_hex"),
                    self._number_value(
                        record.get(
                            "font_relative_luminance"
                        )
                    ),
                    self._number_value(
                        record.get(
                            "background_relative_luminance"
                        )
                    ),
                    self._number_value(
                        record.get(
                            "contrast_ratio"
                        )
                    ),
                    self._number_value(
                        record.get(
                            "contrast_threshold"
                        )
                    ),
                    (
                        record.get(
                            "contrast_level_label"
                        )
                        or record.get(
                            "contrast_level"
                        )
                    ),
                    self._ratio_value(
                        record.get(
                            "background_dominance_ratio"
                        )
                    ),
                    (
                        record.get(
                            "background_sampling_method_label"
                        )
                        or record.get(
                            "background_sampling_method"
                        )
                    ),
                    record.get("contrast_reference"),
                    self._ratio_value(
                        record.get("confidence")
                    ),
                    self._join_values(signal_labels),
                    self._yes_no(
                        record.get("is_near_white")
                    ),
                    self._yes_no(
                        record.get("is_low_contrast")
                    ),
                    self._yes_no(
                        record.get(
                            "is_extreme_low_contrast"
                        )
                    ),
                    self._yes_no(
                        record.get("is_small_text")
                    ),
                    self._yes_no(
                        record.get(
                            "is_relative_small_text"
                        )
                    ),
                    self._yes_no(
                        record.get(
                            "is_instruction_like"
                        )
                    ),
                    record.get("coordinates_label"),
                    self._yes_no(
                        record.get("located")
                    ),
                    record.get("source_image_url"),
                    record.get("annotated_image_url"),
                ]
            )

            row_index = worksheet.max_row

            self._set_hyperlink(
                worksheet.cell(
                    row=row_index,
                    column=32,
                )
            )

            self._set_hyperlink(
                worksheet.cell(
                    row=row_index,
                    column=33,
                )
            )

        for column in ("N", "O"):
            for cell in worksheet[column][1:]:
                if isinstance(
                    cell.value,
                    (int, float),
                ):
                    cell.number_format = "0.0000"

        for column in ("P", "Q"):
            for cell in worksheet[column][1:]:
                if isinstance(
                    cell.value,
                    (int, float),
                ):
                    cell.number_format = (
                        '0.00":1"'
                    )

        for column in ("S", "V"):
            for cell in worksheet[column][1:]:
                if isinstance(
                    cell.value,
                    (int, float),
                ):
                    cell.number_format = "0.0%"

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_column_widths(
            worksheet,
            [
                38, 38, 18, 32, 32, 40, 12, 80, 70,
                28, 18, 20, 24, 24, 24, 18, 18, 32,
                22, 42, 44, 16, 55, 24, 18, 28, 18,
                24, 24, 48, 22, 62, 62,
            ],
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_OcultacaoVisual",
        )

        return len(records)

    def _build_locations_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Tipo de localização",
            "Índice de referência",
            "Código de referência",
            "Detector",
            "Página",
            "Conteúdo localizado",
            "X",
            "Y",
            "Largura",
            "Altura",
            "Confiança",
            "Fonte",
            "Tamanho da fonte",
            "Cor da fonte",
            "Cor estimada do fundo",
            "Razão de contraste",
            "Limiar de contraste",
            "Classificação de contraste",
            "Predominância do fundo",
            "Método de amostragem",
            "Coordenadas",
            "Localizado",
            "Mensagem",
            "Imagem de origem",
            "Imagem anotada",
        ]

        worksheet.append(headers)

        records = export_view.get(
            "locations",
            [],
        )

        if not records:
            worksheet.append(
                [
                    "Nenhuma localização visual foi produzida para este lote.",
                ]
                + [None] * (len(headers) - 1)
            )

        for record in records:
            worksheet.append(
                [
                    record.get("filename"),
                    record.get("analysis_id"),
                    record.get("location_type_label"),
                    record.get("reference_index"),
                    record.get("reference_code"),
                    record.get("detector"),
                    record.get("page_number"),
                    record.get("matched_content"),
                    record.get("left"),
                    record.get("top"),
                    record.get("width"),
                    record.get("height"),
                    self._location_confidence_ratio(record),
                    record.get("font_name"),
                    record.get("font_size"),
                    record.get("font_color_hex"),
                    record.get("background_color_hex"),
                    self._number_value(
                        record.get("contrast_ratio")
                    ),
                    self._number_value(
                        record.get(
                            "contrast_threshold"
                        )
                    ),
                    (
                        record.get(
                            "contrast_level_label"
                        )
                        or record.get(
                            "contrast_level"
                        )
                    ),
                    self._ratio_value(
                        record.get(
                            "background_dominance_ratio"
                        )
                    ),
                    (
                        record.get(
                            "background_sampling_method_label"
                        )
                        or record.get(
                            "background_sampling_method"
                        )
                    ),
                    record.get("coordinates_label"),
                    self._yes_no(
                        record.get("located")
                    ),
                    record.get("message"),
                    record.get("source_image_url"),
                    record.get("annotated_image_url"),
                ]
            )

            row_index = worksheet.max_row

            self._set_hyperlink(
                worksheet.cell(
                    row=row_index,
                    column=26,
                )
            )

            self._set_hyperlink(
                worksheet.cell(
                    row=row_index,
                    column=27,
                )
            )

        for cell in worksheet["M"][1:]:
            if isinstance(
                cell.value,
                (int, float),
            ):
                cell.number_format = "0.0%"

        for column in ("R", "S"):
            for cell in worksheet[column][1:]:
                if isinstance(
                    cell.value,
                    (int, float),
                ):
                    cell.number_format = (
                        '0.00":1"'
                    )

        for cell in worksheet["U"][1:]:
            if isinstance(
                cell.value,
                (int, float),
            ):
                cell.number_format = "0.0%"

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_column_widths(
            worksheet,
            [
                38, 38, 28, 18, 34, 42, 12, 80,
                14, 14, 14, 14, 16, 28, 18, 20,
                24, 18, 18, 32, 22, 42, 48, 14,
                60, 62, 62,
            ],
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_Localizacoes",
        )

        return len(records)

    def _build_technical_data_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Enviado em",
            "Tamanho em bytes",
            "Tamanho formatado",
            "SHA-256",
            "Páginas",
            "Título do PDF",
            "Autor do PDF",
            "Criador do PDF",
            "Produtor do PDF",
            "Data de criação",
            "Data de modificação",
            "Versão do PDF",
            "Possui texto nativo",
            "Caracteres de texto nativo",
            "Páginas com texto nativo",
            "Caracteres OCR",
            "Páginas processadas por OCR",
            "Páginas com texto OCR",
            "Idioma OCR",
            "Documento normalizado",
            "Páginas normalizadas",
            "Text spans normalizados",
            "Palavras normalizadas",
            "Caracteres normalizados",
            "Caracteres após normalização",
            "Páginas normalizadas com texto",
            "Imagens extraídas",
            "Fingerprints de imagem",
            "Códigos de barras",
            "Formatos de código",
            "Páginas com código",
            "Sequências numéricas",
            "Fontes das sequências",
            "Dígitos em sequências",
            "Linhas válidas",
            "Linhas inválidas",
            "Linhas inconclusivas",
            "Comparações compatíveis",
            "Comparações divergentes",
            "Comparações inconclusivas",
            "Total de evidências",
        ]

        worksheet.append(headers)

        records = export_view.get(
            "technical_data",
            [],
        )

        if not records:
            worksheet.append(
                [
                    "Nenhum dado técnico foi disponibilizado para exportação.",
                ]
                + [None] * (len(headers) - 1)
            )

        for record in records:
            worksheet.append(
                [
                    record.get("filename"),
                    record.get("analysis_id"),
                    record.get("uploaded_at"),
                    record.get("size_bytes"),
                    record.get("formatted_size"),
                    record.get("sha256"),
                    record.get("page_count"),
                    record.get("pdf_title"),
                    record.get("pdf_author"),
                    record.get("pdf_creator"),
                    record.get("pdf_producer"),
                    record.get("pdf_creation_date"),
                    record.get("pdf_modification_date"),
                    record.get("pdf_version"),
                    self._yes_no(
                        record.get("has_native_text")
                    ),
                    record.get("native_text_character_count"),
                    record.get("native_text_pages", 0),
                    record.get("ocr_character_count"),
                    record.get("ocr_pages_processed"),
                    record.get("ocr_pages_with_text", 0),
                    record.get("ocr_language"),
                    self._yes_no(
                        record.get("has_normalized_document")
                    ),
                    record.get("normalized_document_page_count"),
                    record.get("normalized_document_text_span_count"),
                    record.get("normalized_document_word_count"),
                    record.get("normalized_document_character_count"),
                    record.get(
                        "normalized_document_normalized_character_count"
                    ),
                    record.get(
                        "normalized_document_pages_with_text"
                    ),
                    record.get("image_count"),
                    record.get("image_fingerprint_count"),
                    record.get("barcode_count"),
                    record.get("barcode_formats"),
                    record.get("barcode_pages"),
                    record.get("printed_numeric_line_count"),
                    record.get("printed_numeric_line_sources"),
                    record.get("printed_numeric_digit_total"),
                    record.get("valid_numeric_line_count"),
                    record.get("invalid_numeric_line_count"),
                    record.get("inconclusive_numeric_line_count"),
                    record.get("barcode_line_match_count"),
                    record.get("barcode_line_mismatch_count"),
                    record.get("barcode_line_inconclusive_count"),
                    record.get("evidence_count"),
                ]
            )

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_column_widths(
            worksheet,
            [
                38, 38, 24, 18, 20, 68, 12, 36, 32, 32, 32,
                24, 24, 16, 20, 24, 28, 18, 24, 24, 16, 22,
                20, 22, 22, 24, 26, 26, 18, 22, 18, 28, 22,
                22, 28, 20, 16, 16, 18, 20, 20, 20, 18,
            ],
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_DadosTecnicos",
        )

        return len(records)

    def _build_images_sheet(
        self,
        worksheet,
        export_view: dict[str, Any],
    ) -> int:
        headers = [
            "Documento",
            "ID da análise",
            "Imagens extraídas no documento",
            "Índice do fingerprint",
            "Página",
            "Largura",
            "Altura",
            "MIME type",
            "DPI",
            "Descrição",
            "Confiança",
            "SHA-256 da imagem",
            "Perceptual hash",
            "Average hash",
            "Difference hash",
            "Posição X",
            "Posição Y",
            "Largura da região",
            "Altura da região",
        ]

        worksheet.append(headers)

        records = export_view.get(
            "images",
            [],
        )

        if not records:
            worksheet.append(
                [
                    "Nenhum fingerprint de imagem foi produzido para este lote.",
                ]
                + [None] * (len(headers) - 1)
            )

        for record in records:
            worksheet.append(
                [
                    record.get("filename"),
                    record.get("analysis_id"),
                    record.get("total_extracted_images"),
                    record.get("fingerprint_index"),
                    record.get("page_number"),
                    record.get("width"),
                    record.get("height"),
                    record.get("mime_type"),
                    record.get("dpi"),
                    record.get("description"),
                    record.get("confidence"),
                    record.get("image_hash"),
                    record.get("perceptual_hash"),
                    record.get("average_hash"),
                    record.get("difference_hash"),
                    record.get("location_x"),
                    record.get("location_y"),
                    record.get("location_width"),
                    record.get("location_height"),
                ]
            )

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
        )

        self._set_column_widths(
            worksheet,
            [
                38, 38, 26, 22, 12, 14, 14, 22, 16, 54,
                18, 68, 38, 38, 38, 16, 16, 20, 20,
            ],
        )

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_Imagens",
        )

        return len(records)

    def _build_comparisons_sheet(
        self,
        worksheet,
        evidences: list[DocumentEvidence],
        total_documents: int,
        identifier_comparisons: list[dict[str, Any]] | None = None,
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
            "Campo identificado", "Valor 1", "Valor 2 / relação", "Proveniência",
        ]

        worksheet.append(headers)

        exported_comparisons = 0

        if not evidences and not identifier_comparisons:
            if total_documents == 1:
                message = (
                    "Comparação entre documentos não aplicável: "
                    "este lote contém apenas um documento. "
                    "São necessários dois ou mais documentos para "
                    "análises comparativas."
                )
            else:
                message = (
                    "Nenhum apontamento comparativo foi identificado "
                    "entre os documentos deste lote."
                )

            worksheet.append(
                [message]
                + [None] * (len(headers) - 1)
            )

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
                    None, None, None, None,
                ]
            )

            exported_comparisons += 1

        for item in identifier_comparisons or []:
            if not isinstance(item, dict):
                continue
            participants = item.get("participants") or []
            names = [str(p.get("filename") or "") for p in participants]
            provenances = [
                f"{p.get('filename')}: pág. {p.get('page_number') or '?'} "
                f"({p.get('source') or '?'})"
                for p in participants
            ]
            worksheet.append([
                self._safe_financial_excel_text(item.get("code")),
                self._safe_financial_excel_text(item.get("label")),
                self._safe_financial_excel_text(item.get("description")),
                self._safe_financial_excel_text(item.get("severity")),
                None, None,
                item.get("document_count"),
                self._safe_financial_excel_text(" | ".join(names)),
                None, "DocumentIdentifierService (observacional)",
                self._safe_financial_excel_text(item.get("kind")),
                self._safe_financial_excel_text(item.get("value")),
                self._safe_financial_excel_text(
                    item.get("other_value") or item.get("relation")
                ),
                self._safe_financial_excel_text(" | ".join(provenances)),
            ])
            exported_comparisons += 1

        self._style_worksheet(
            worksheet=worksheet,
            freeze_panes="A2",
            auto_filter=False,
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
            "K": 24, "L": 36, "M": 28, "N": 72,
        }

        for column, width in column_widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

        self._add_excel_table(
            worksheet=worksheet,
            table_name="DocDNA_Comparacoes",
        )

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

            roles = {x.get("value"): x.get("role")
                     for x in document.get("numeric_line_contexts", [])}
            role_labels = {
                "payment_line_candidate": "candidata de pagamento; vínculo não confirmado",
                "unresolved_numeric_sequence": "sequência inconclusiva",
            }
            normalized_lines = self._join_values([
                str(value) + (f" [{role_labels[roles[value]]}]" if roles.get(value) in role_labels else "")
                for value in numeric_lines
            ])

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
            ) + (
                " [campos concatenados; observação preservada]"
                if self._safe_attribute(line, "contextual_kind") == "concatenated_fields" else
                " [candidata de pagamento; vínculo não confirmado]"
                if self._safe_attribute(line, "contextual_kind") == "payment_line_candidate" else
                " [sequência numérica inconclusiva]"
                if self._safe_attribute(line, "contextual_kind") == "unresolved_numeric_sequence" else ""
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
            38,  # Documento
            18,  # Status operacional
            24,  # Situação analítica
            18,  # Código analítico
            28,  # Possui apontamentos comparativos
            22,  # Quantidade de apontamentos comparativos
            26,  # Maior severidade comparativa
            23,  # Referência comparativa
            38,  # ID análise
            18,  # Tamanho
            68,  # SHA
            12,  # Páginas
            30,  # Título
            26,  # Autor
            30,  # Produtor
            24,  # Criação
            24,  # Modificação
            54,  # ITF
            70,  # QR
            34,  # Code39
            52,  # Outros
            70,  # Sequências
            24,  # Fontes
            70,  # Validações
            80,  # Comparações
            18,  # Evidências
            44,  # Localização
            46,  # Erro
            28,  # Triagem técnica
            65,  # Motivos
            47,  # Códigos comparativos relevantes
            22,  # Inválidas
            22,  # Divergências
            22,  # Registros inconclusivos
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

    def _add_excel_table(
        self,
        *,
        worksheet,
        table_name: str,
    ) -> None:
        if worksheet.max_row < 2:
            return

        reference = (
            f"A1:"
            f"{get_column_letter(worksheet.max_column)}"
            f"{worksheet.max_row}"
        )

        table = Table(
            displayName=table_name,
            ref=reference,
        )

        style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        table.tableStyleInfo = style

        worksheet.add_table(
            table
        )

    def _style_document_statuses(
        self,
        worksheet,
    ) -> None:
        fills = {
            "alert": "FCE8EC",
            "attention": "FFF4D6",
            "clear": "EAF6EE",
            "not_executed": "EEF2F6",
        }

        fonts = {
            "alert": "9F1239",
            "attention": "92400E",
            "clear": "166534",
            "not_executed": "475569",
        }

        for row_index in range(
            2,
            worksheet.max_row + 1,
        ):
            label_cell = worksheet.cell(
                row=row_index,
                column=3,
            )

            code_cell = worksheet.cell(
                row=row_index,
                column=4,
            )

            status = str(
                code_cell.value or ""
            ).strip()

            fill_color = fills.get(
                status
            )

            font_color = fonts.get(
                status
            )

            if fill_color:
                label_cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor=fill_color,
                )

            if font_color:
                label_cell.font = Font(
                    color=font_color,
                    bold=True,
                )

    def _style_summary_statuses(
        self,
        *,
        worksheet,
        analytical_status: str,
    ) -> None:
        fills = {
            "alert": "FCE8EC",
            "attention": "FFF4D6",
            "clear": "EAF6EE",
            "not_executed": "EEF2F6",
        }

        fonts = {
            "alert": "9F1239",
            "attention": "92400E",
            "clear": "166534",
            "not_executed": "475569",
        }

        for row_index in range(
            2,
            worksheet.max_row + 1,
        ):
            label = worksheet.cell(
                row=row_index,
                column=1,
            ).value

            if label != "Situação analítica":
                continue

            value_cell = worksheet.cell(
                row=row_index,
                column=2,
            )

            fill_color = fills.get(
                analytical_status
            )

            font_color = fonts.get(
                analytical_status
            )

            if fill_color:
                value_cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor=fill_color,
                )

            if font_color:
                value_cell.font = Font(
                    color=font_color,
                    bold=True,
                )

            break

    def _set_column_widths(
        self,
        worksheet,
        widths: list[int],
    ) -> None:
        for index, width in enumerate(
            widths,
            start=1,
        ):
            worksheet.column_dimensions[
                get_column_letter(index)
            ].width = width

    def _number_value(
        self,
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _location_confidence_ratio(self, record: dict[str, Any]) -> float | None:
        value = record.get("confidence")
        if record.get("location_type") != "numeric_line":
            return self._ratio_value(value)
        # NumericLineLocation preserva a média OCR original em 0–100.
        # Mesmo 0.5 significa 0.5%, não 50%. Não adivinhar a escala pelo valor.
        try:
            percent = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(percent) or not 0 <= percent <= 100:
            return None
        return percent / 100

    def _ratio_value(
        self,
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            ratio = float(value)
        except (TypeError, ValueError):
            return None

        return min(
            max(ratio, 0.0),
            1.0,
        )

    @classmethod
    def _sanitize_excel_text(
        cls,
        value: str,
    ) -> str:
        """
        Converte caracteres incompatíveis com XLSX em representação visível.

        O conteúdo analítico original não é modificado. Esta transformação
        existe somente na fronteira de exportação para Excel.

        Em vez de remover silenciosamente um caractere de controle, ele é
        representado como \\xNN para preservar sua existência no relatório.
        """

        if not isinstance(value, str):
            raise TypeError(
                "Excel text sanitizer value must be a string."
            )

        return cls._EXCEL_ILLEGAL_CHARACTERS.sub(
            lambda match: (
                f"\\x{ord(match.group(0)):02X}"
            ),
            value,
        )

    @classmethod
    def _sanitize_excel_payload(
        cls,
        value: Any,
    ) -> Any:
        """
        Sanitiza recursivamente a estrutura preparada para exportação.

        Strings recebem tratamento específico para XLSX. Coleções mantêm
        sua estrutura original e valores não textuais permanecem intactos.
        """

        if isinstance(value, str):
            return cls._sanitize_excel_text(
                value
            )

        if isinstance(value, dict):
            return {
                key: cls._sanitize_excel_payload(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                cls._sanitize_excel_payload(
                    item
                )
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                cls._sanitize_excel_payload(
                    item
                )
                for item in value
            )

        if isinstance(value, set):
            return {
                cls._sanitize_excel_payload(
                    item
                )
                for item in value
            }

        return value

    def _format_json_value(
        self,
        value: Any,
    ) -> str:
        if value in (None, "", [], {}, ()):
            return ""

        if isinstance(value, str):
            return value

        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
            )
        except (TypeError, ValueError):
            return str(value)

    def _yes_no(
        self,
        value: Any,
    ) -> str:
        return "Sim" if bool(value) else "Não"

    def _set_hyperlink(
        self,
        cell,
    ) -> None:
        value = cell.value

        if value is None:
            return

        target = str(value).strip()

        if not target:
            return

        cell.hyperlink = target
        cell.style = "Hyperlink"

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
