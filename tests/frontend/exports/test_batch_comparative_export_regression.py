"""Testes de regressão do CF-QA 001: contexto comparativo no Excel.

Estes testes descrevem o comportamento desejado antes da correção.
Enquanto o defeito existir, alguns testes DEVEM falhar (fase RED do TDD).
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from openpyxl import Workbook

from app.domain.models.batch import Batch, BatchStatus
from app.domain.models.batch_document import (
    BatchDocument,
    BatchDocumentStatus,
)
from app.domain.models.batch_result import BatchResult
from app.domain.services import batch_excel_export_service as export_module
from app.domain.services.batch_excel_export_service import (
    BatchExcelExportService,
)
from app.frontend.exports.batch_export_view_builder import (
    BatchExportViewBuilder,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.config.settings import settings


def _document(filename: str) -> BatchDocument:
    """Cria um documento fictício, sem depender de PDFs reais."""
    return BatchDocument(
        document_id=uuid4(),
        original_filename=filename,
        status=BatchDocumentStatus.COMPLETED,
        analysis_id=uuid4(),
        error_message=None,
    )


def _batch(documents: list[BatchDocument]) -> Batch:
    """Cria um lote de teste com seus contadores coerentes."""
    now = datetime.now()

    return Batch(
        id=uuid4(),
        created_at=now,
        started_at=now,
        finished_at=now,
        status=BatchStatus.COMPLETED,
        documents=documents,
        result=BatchResult(
            total_documents=len(documents),
            pending_documents=0,
            processing_documents=0,
            completed_documents=len(documents),
            failed_documents=0,
            progress_percentage=100.0,
        ),
    )


def test_export_view_repassa_achados_comparativos_sem_alterar_status():
    """Um achado de lote não pode converter CLEAR em ALERT."""
    document = _document("sem_linha.pdf")
    batch = _batch([document])

    statuses = {
        str(document.analysis_id): InvestigationStatus.CLEAR
    }

    builder = BatchExportViewBuilder()

    # A visão interna já suporta contexto comparativo.
    # Criamos uma resposta controlada para testar somente
    # a propagação dos dados pelo exportador.
    batch_view = builder._batch_view_builder.build(
        batch=batch,
        document_analytical_statuses=statuses,
    )

    batch_view["documents"][0].update(
        has_comparative_findings=True,
        comparative_finding_count=1,
        comparative_highest_severity_label="Informativo",
        comparative_url="/batches/exemplo/comparisons",
    )

    builder._batch_view_builder.build = Mock(
        return_value=batch_view
    )

    finding = object()

    result = builder.build(
        batch=batch,
        document_analytical_statuses=statuses,
        comparative_findings=[finding],
    )

    # Os findings devem chegar ao BatchViewBuilder.
    kwargs = builder._batch_view_builder.build.call_args.kwargs

    assert kwargs["comparative_findings"] == [finding]

    exported = result["documents"][0]

    assert exported["analytical_status"] == "clear"
    assert exported["analytical_status_label"] == "Sem apontamentos"
    assert exported["has_comparative_findings"] is True
    assert exported["comparative_finding_count"] == 1

    assert (
            exported["comparative_highest_severity_label"]
            == "Informativo"
    )

    # O resumo de risco individual permanece intacto.
    assert result["summary"]["clear_documents"] == 1
    assert result["summary"]["alert_documents"] == 0


def test_export_view_sem_achados_de_lote_informa_quantidade_zero():
    """Não inventa achados comparativos quando não existem."""
    document = _document("limpo.pdf")

    result = BatchExportViewBuilder().build(
        batch=_batch([document]),
        document_analytical_statuses={
            str(document.analysis_id): InvestigationStatus.CLEAR,
        },
    )

    exported = result["documents"][0]

    assert exported["analytical_status"] == "clear"
    assert exported["has_comparative_findings"] is False
    assert exported["comparative_finding_count"] == 0


def test_servico_encaminha_findings_para_visao_de_exportacao():
    """O serviço entrega ao export builder os findings calculados."""
    service = BatchExcelExportService()

    service._finding_aggregation_service.aggregate = Mock(
        return_value=[]
    )

    service._export_view_builder.build = Mock(
        return_value={}
    )

    finding = object()
    batch = _batch([])

    service._build_export_view(
        batch,
        comparative_findings=[finding],
    )

    kwargs = service._export_view_builder.build.call_args.kwargs

    assert kwargs["comparative_findings"] == [finding]


def test_aba_documentos_exibe_contexto_comparativo_por_documento():
    """As colunas devem exibir a comparação sem modificar o status."""
    document = _document("sem_linha.pdf")
    batch = _batch([document])

    service = BatchExcelExportService()

    service._get_analysis = Mock(
        return_value={}
    )

    export_view = {
        "documents": [
            {
                "analysis_id": str(document.analysis_id),
                "analytical_status": "clear",
                "analytical_status_label": "Sem apontamentos",
                "has_comparative_findings": True,
                "comparative_finding_count": 1,
                "comparative_highest_severity_label": "Informativo",
                "comparative_url": "/batches/exemplo/comparisons",
            }
        ]
    }

    worksheet = Workbook().active

    service._build_documents_sheet(
        worksheet=worksheet,
        batch=batch,
        export_view=export_view,
    )

    row = {
        cell.value: worksheet.cell(
            row=2,
            column=index,
        ).value
        for index, cell in enumerate(
            worksheet[1],
            start=1,
        )
        if isinstance(cell.value, str)
    }

    assert row["Situação analítica"] == "Sem apontamentos"
    assert row["Código analítico"] == "clear"

    assert (
            row["Possui apontamentos comparativos"]
            == "Sim"
    )

    assert (
            row["Quantidade de apontamentos comparativos"]
            == 1
    )

    assert (
            row["Maior severidade comparativa"]
            == "Informativo"
    )

    assert (
            row["Referência comparativa"]
            == "08 - Comparações"
    )


def test_exportacao_executa_validacao_cruzada_apenas_uma_vez(
        tmp_path: Path,
        monkeypatch,
):
    """O Excel reutiliza a mesma execução comparativa."""
    monkeypatch.setattr(
        settings,
        "REPORTS_DIR",
        tmp_path,
    )

    batch = _batch([])
    service = BatchExcelExportService()

    finding = object()

    cross_validation = Mock()

    cross_validation.execute_with_report.return_value = (
        SimpleNamespace(findings=[finding]),
        SimpleNamespace(
            evidences=[],
            highest_severity=None,
        ),
    )

    cross_validation.build_evidence_report.side_effect = (
        AssertionError(
            "A exportação não deve recalcular "
            "o relatório comparativo."
        )
    )

    service._cross_validation_service = cross_validation

    build_export_view = Mock(
        return_value={}
    )

    service._build_export_view = build_export_view

    # Substituímos apenas a escrita das abas.
    # A função export() continua real,
    # inclusive a gravação do XLSX.
    for name in (
            "_build_documents_sheet",
            "_build_findings_sheet",
            "_build_evidences_sheet",
            "_build_financial_sheet",
            "_build_prompt_injection_sheet",
            "_build_concealment_sheet",
            "_build_locations_sheet",
            "_build_technical_data_sheet",
            "_build_images_sheet",
            "_build_comparisons_sheet",
    ):
        setattr(
            service,
            name,
            Mock(return_value=0),
        )

    service._build_summary_sheet = Mock(
        return_value=None
    )

    exported = service.export(batch)

    cross_validation.execute_with_report.assert_called_once_with(
        batch
    )

    cross_validation.build_evidence_report.assert_not_called()

    assert (
            build_export_view.call_args.kwargs["comparative_findings"]
            == [finding]
    )

    assert Path(exported["file_path"]).is_file()
