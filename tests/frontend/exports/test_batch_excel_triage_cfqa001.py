"""Regressões de visibilidade da triagem na exportação de lotes do DocDNA."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from openpyxl import Workbook

from app.domain.services.batch_excel_export_service import BatchExcelExportService


def _document(filename: str):
    """Cria um documento mínimo para testar o relatório sem carregar PDF."""
    return SimpleNamespace(
        document_id=uuid4(),
        analysis_id=uuid4(),
        original_filename=filename,
        status=SimpleNamespace(value="completed"),
        error_message=None,
    )


def _view(*documents):
    """Prepara status individuais sem executar detectores."""
    return {
        "documents": [
            {
                "analysis_id": str(item.analysis_id),
                "analytical_status": "clear",
                "analytical_status_label": "Sem apontamentos",
                "comparative_finding_count": 1,
                "comparative_highest_severity_label": "Informativo",
            }
            for item in documents
        ],
        "financial": [],
    }


def test_contextual_invalidity_is_visible_without_changing_strict_validation_count():
    document = _document("contextual.pdf")
    other = _document("other.pdf")
    view = _view(document, other)
    view["contextual_payment_line_findings"] = [{
        "analysis_id": str(document.analysis_id),
        "code": "PAYMENT_LINE_INVALID_STRUCTURE",
    }]
    view["financial"] = [{
        "analysis_id": str(document.analysis_id),
        "record_type": "validation", "status": "inconclusive",
    }]
    records = BatchExcelExportService()._build_triage_records(
        batch=SimpleNamespace(documents=[document, other]),
        export_view=view, comparative_evidences=[],
    )
    by_id = {r["analysis_id"]: r for r in records}
    record = by_id[str(document.analysis_id)]
    assert record["contextual_invalid_count"] == 1
    assert record["invalid_count"] == 0
    assert record["inconclusive_count"] == 1
    assert record["triage_priority"] == 1
    assert record["analytical_status_label"] == "Sem apontamentos"
    assert "não equivale ao status INVALID" in record["reasons"]
    assert "03 - Evidências" in record["reasons"]
    assert by_id[str(other.analysis_id)]["contextual_invalid_count"] == 0


def test_missing_identifiers_are_reported_as_extraction_limits_without_raising_priority():
    document = _document("fields.pdf")
    view = _view(document)
    view["identifier_observations"] = [{
        "analysis_id": str(document.analysis_id), "kind": "account", "value": "000012345678",
    }]
    [record] = BatchExcelExportService()._build_triage_records(
        batch=SimpleNamespace(documents=[document]), export_view=view,
        comparative_evidences=[],
    )
    assert "Débito automático" in record["reasons"]
    assert "Titular informado" in record["reasons"]
    assert "Ausência de leitura não confirma ausência" in record["reasons"]
    assert record["triage_priority"] == 5


def test_itf_repetido_aparece_na_triagem_sem_inventar_divergencia_financeira():
    """ITF repetido é um fato; diferença entre valores ainda não comprovada."""
    a, b = _document("a.pdf"), _document("b.pdf")
    lote = SimpleNamespace(documents=[a, b])
    evidencia = SimpleNamespace(
        code="DUPLICATE_ITF",
        document_ids=[str(a.document_id), str(b.document_id)],
        metadata={"document_names": ["a.pdf", "b.pdf"]},
    )
    service = BatchExcelExportService()
    records = service._build_triage_records(
        batch=lote,
        export_view=_view(a, b),
        comparative_evidences=[evidencia],
    )

    assert len(records) == 2
    for record in records:
        assert record["analytical_status_label"] == "Sem apontamentos"
        assert record["triage_label"] == "Conferir comparação entre documentos"
        assert record["comparative_codes"] == ["DUPLICATE_ITF"]
        assert record["mismatch_count"] == 0
        assert "Código ITF repetido" in record["reasons"]


def test_conta_resultados_financeiros_sem_tratar_inconclusivo_como_divergencia():
    """Invalid, mismatch e inconclusive são três estados diferentes."""
    document = _document("c.pdf")
    view = _view(document)
    analysis_id = str(document.analysis_id)
    view["financial"] = [
        {"analysis_id": analysis_id, "record_type": "validation", "status": "invalid"},
        {"analysis_id": analysis_id, "record_type": "comparison", "status": "mismatch"},
        {"analysis_id": analysis_id, "record_type": "comparison", "status": "inconclusive"},
        {"analysis_id": analysis_id, "record_type": "validation", "status": "inconclusive"},
    ]
    record = BatchExcelExportService()._build_triage_records(
        batch=SimpleNamespace(documents=[document]),
        export_view=view,
        comparative_evidences=[],
    )[0]

    assert record["invalid_count"] == 1
    assert record["mismatch_count"] == 1
    assert record["inconclusive_count"] == 2
    assert record["triage_priority"] == 1
    assert "sem confirmação de divergência" in record["reasons"]


def test_metadados_ambiguos_nao_associam_alerta_ao_documento_errado():
    """Nome duplicado não deve atribuir um finding a todos os homônimos."""
    a, b = _document("repetido.pdf"), _document("repetido.pdf")
    evidence = SimpleNamespace(
        code="DUPLICATE_ITF",
        document_ids=[str(a.document_id)],
        metadata={"document_names": ["repetido.pdf"]},
    )
    records = BatchExcelExportService()._build_triage_records(
        batch=SimpleNamespace(documents=[a, b]),
        export_view=_view(a, b),
        comparative_evidences=[evidence],
    )
    by_id = {record["analysis_id"]: record for record in records}
    assert by_id[str(a.analysis_id)]["comparative_codes"] == ["DUPLICATE_ITF"]
    assert by_id[str(b.analysis_id)]["comparative_codes"] == []


def test_aba_triagem_e_documentos_mostram_motivo_sem_deslocar_colunas_antigas():
    """Preserva as 34 colunas anteriores e adiciona 5 campos cadastrais ao final."""
    document = _document("fatura.pdf")
    record = BatchExcelExportService()._build_triage_records(
        batch=SimpleNamespace(documents=[document]),
        export_view=_view(document),
        comparative_evidences=[],
    )[0]
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value={})

    triage_sheet = Workbook().active
    service._build_triage_sheet(worksheet=triage_sheet, records=[record])
    triage_headers = [cell.value for cell in triage_sheet[1]]
    assert "Motivos para revisão / limitações" in triage_headers
    assert "Triagem técnica (não altera status)" in triage_headers

    docs_sheet = Workbook().active
    export_view = _view(document)
    export_view["identifier_observations"] = [
        {
            "analysis_id": str(document.analysis_id),
            "kind": "account",
            "value": "00001234000056",
        }
    ]
    service._build_documents_sheet(
        worksheet=docs_sheet,
        batch=SimpleNamespace(documents=[document]),
        export_view=export_view,
        triage_by_analysis_id={str(document.analysis_id): record},
    )
    headers = [cell.value for cell in docs_sheet[1]]
    assert headers[2] == "Situação analítica"
    assert headers[3] == "Código analítico"
    assert headers[27] == "Erro de processamento"
    assert headers[28] == "Triagem técnica (não altera status individual)"
    # As 34 colunas históricas não devem desaparecer, mudar de nome
    # nem ser deslocadas. O CF-QA 003.6 APENAS acrescenta cinco ao final.
    original_headers = [
        "Documento", "Status no lote", "Situação analítica",
        "Código analítico", "Possui apontamentos comparativos",
        "Quantidade de apontamentos comparativos",
        "Maior severidade comparativa", "Referência comparativa",
        "ID da análise", "Tamanho em bytes", "SHA-256", "Páginas",
        "Título do PDF", "Autor do PDF", "Produtor do PDF",
        "Data de criação", "Data de modificação", "ITF", "QR Code",
        "Code 39", "Outros códigos", "Sequências numéricas",
        "Fontes das sequências", "Validações estruturais",
        "Comparações linha × código", "Total de evidências",
        "Status da localização visual", "Erro de processamento",
        "Triagem técnica (não altera status individual)",
        "Motivos para revisão / limitações",
        "Códigos comparativos relevantes",
        "Validações numéricas inválidas",
        "Divergências linha × código",
        "Registros financeiros inconclusivos",
    ]
    new_headers = [
        "Conta identificada", "Cliente identificado", "Fatura identificada",
        "Débito automático identificado", "Titular informado",
    ]

    assert headers[:34] == original_headers
    assert headers[34:] == new_headers
    assert docs_sheet.max_column == len(headers) == 39
    assert docs_sheet.cell(row=2, column=29).value == record["triage_label"]
    assert docs_sheet.cell(row=2, column=35).value == "00001234000056"
    assert docs_sheet.cell(row=2, column=3).value == "Sem apontamentos"
