"""CF-QA 002.3: rastreabilidade de reconciliação financeira no XLSX.

Testes sintéticos e independentes de operadora, valores ou lote real.
O resultado observacional NUNCA altera a situação analítica individual.
"""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from openpyxl import Workbook, load_workbook

from app.domain.services import batch_excel_export_service as export_module
from app.domain.services.batch_excel_export_service import BatchExcelExportService


def _document(filename="conta.pdf"):
    return SimpleNamespace(
        document_id=uuid4(),
        analysis_id=uuid4(),
        original_filename=filename,
        status=SimpleNamespace(value="completed"),
        error_message=None,
    )


def _batch(*documents):
    return SimpleNamespace(
        id=uuid4(),
        documents=list(documents),
        result=SimpleNamespace(total_documents=len(documents)),
    )


def _analysis(status="REVIEW_REQUIRED", values=None, issues=None):
    return {"financial_reconciliation": {
        "status": status,
        "message": "Diferença observada; vínculo a confirmar.",
        "issues": issues if issues is not None else [],
        "values": values if values is not None else [
            {"source": "ITF", "amount": "154.23", "page_number": 1,
             "barcode_index": 2, "raw_content": "8" * 44,
             "provenance": "FEBRABAN_ARRECADACAO_44_DV_GERAL"},
            {"source": "PIX", "amount": "1.00", "page_number": 1,
             "barcode_index": 3, "raw_content": "000201valor-sintetico",
             "provenance": "PIX_BR_CODE_TLV_CRC16_CAMPO_54"},
        ],
    }}


def test_dados_reais_do_repositorio_sem_reexecutar_detectores():
    doc = _document()
    batch = _batch(doc)
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis())
    result = service._build_financial_reconciliation_records(batch)
    assert len(result) == 1
    assert result[0]["analysis_id"] == str(doc.analysis_id)
    assert result[0]["values"][0]["amount"] == "154.23"
    service._get_analysis.assert_called_once_with(doc.analysis_id)


def test_documentos_antigos_nao_recebem_reconciliacao_inventada():
    doc = _document("antigo.pdf")
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value={})
    assert service._build_financial_reconciliation_records(_batch(doc)) == []


def test_resultado_inconclusivo_sem_valores_ainda_tem_linha_de_resumo():
    doc = _document()
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis(
        status="INCONCLUSIVE", values=[], issues=["Pix sem campo de valor"],
    ))
    records = service._build_financial_reconciliation_records(_batch(doc))
    ws = Workbook().active
    count = service._build_financial_reconciliation_sheet(worksheet=ws, records=records)
    assert count == 1
    assert ws.cell(2, 3).value == "Resumo"
    assert ws.cell(2, 4).value == "Inconclusivo"
    assert "Pix sem campo" in ws.cell(2, 13).value


def test_valores_separados_por_fonte_com_pagina_e_hash():
    doc = _document()
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis())
    records = service._build_financial_reconciliation_records(_batch(doc))
    ws = Workbook().active
    count = service._build_financial_reconciliation_sheet(worksheet=ws, records=records)
    assert count == 3
    assert ws.cell(3, 5).value == "ITF"
    assert ws.cell(3, 6).value == "154.23"  # string, sem perda de centavos
    assert ws.cell(3, 7).value == 1
    assert len(ws.cell(3, 11).value) == 64
    assert ws.cell(4, 5).value == "PIX"
    assert ws.cell(4, 6).value == "1.00"
    assert ws.cell(4, 4).value is None  # status pertence ao RESUMO, não ao valor


def test_texto_impresso_agregado_nao_recebe_pagina_inventada():
    doc = _document()
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis(
        status="INCONCLUSIVE", values=[
            {"source": "PRINTED", "amount": "345.67",
             "page_number": None, "barcode_index": None,
             "raw_content": "Total a pagar: R$ 345,67",
             "provenance": "TEXT_TOTAL_LABEL:ocr"},
        ],
    ))
    ws = Workbook().active
    service._build_financial_reconciliation_sheet(
        worksheet=ws,
        records=service._build_financial_reconciliation_records(_batch(doc)),
    )
    assert ws.cell(3, 5).value == "PRINTED"
    assert ws.cell(3, 7).value is None
    assert ws.cell(3, 8).value is None


def test_payload_hostil_nao_e_gravado_como_formula():
    doc = _document()
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis(values=[{
        "source": "PRINTED", "amount": "9.99", "page_number": None,
        "barcode_index": None, "provenance": "OCR",
        "raw_content": '=HYPERLINK("https://example.org", "clique")',
    }]))
    ws = Workbook().active
    service._build_financial_reconciliation_sheet(
        worksheet=ws,
        records=service._build_financial_reconciliation_records(_batch(doc)),
    )
    assert ws.cell(3, 10).value.startswith("'=")
    assert ws.cell(3, 10).data_type != "f"


def test_triagem_sinaliza_valores_distintos_sem_modificar_status_individual():
    doc = _document()
    service = BatchExcelExportService()
    records = service._build_triage_records(
        batch=_batch(doc),
        export_view={"documents": [{
            "analysis_id": str(doc.analysis_id),
            "analytical_status_label": "Sem apontamentos",
            "comparative_finding_count": 0,
        }], "financial": []},
        comparative_evidences=[],
        financial_reconciliations=[{
            "analysis_id": str(doc.analysis_id),
            "status": "REVIEW_REQUIRED", "issues": [],
        }],
    )
    assert len(records) == 1
    assert records[0]["analytical_status_label"] == "Sem apontamentos"
    assert records[0]["triage_priority"] == 2
    assert "vínculo" in records[0]["reasons"]
    assert "04 - Financeiro" in records[0]["reasons"]
    assert records[0]["mismatch_count"] == 0  # não promove a MISMATCH


def test_exportacao_unificada_preserva_registros_e_retira_abas_a(tmp_path, monkeypatch):
    """A reconciliação permanece rastreável na aba 04, sem abas intermediárias."""
    monkeypatch.setattr(
        export_module, "settings", SimpleNamespace(REPORTS_DIR=tmp_path),
    )
    doc = _document()
    service = BatchExcelExportService()
    service._get_analysis = Mock(return_value=_analysis())
    service._cross_validation_service.execute_with_report = Mock(return_value=(
        SimpleNamespace(findings=[]),
        SimpleNamespace(evidences=[], highest_severity=None),
    ))
    service._build_export_view = Mock(return_value={
        "documents": [{
            "analysis_id": str(doc.analysis_id),
            "analytical_status_label": "Sem apontamentos",
            "comparative_finding_count": 0,
        }],
        "financial": [],
    })
    service._build_summary_sheet = Mock()
    for method in (
        "_build_documents_sheet", "_build_findings_sheet",
        "_build_evidences_sheet",
        "_build_prompt_injection_sheet", "_build_concealment_sheet",
        "_build_locations_sheet", "_build_comparisons_sheet",
        "_build_technical_data_sheet", "_build_images_sheet",
    ):
        setattr(service, method, Mock(return_value=0))
    exported = service.export(_batch(doc))
    wb = load_workbook(exported["file_path"], read_only=True)
    try:
        assert "04 - Financeiro" in wb.sheetnames
        assert "04A - Reconciliação" not in wb.sheetnames
        assert "00A - Triagem" not in wb.sheetnames
        assert "00 - Resumo" in wb.sheetnames
        assert "01 - Documentos" in wb.sheetnames
        ws = wb["04 - Financeiro"]
        assert ws.max_row == 4  # header, resumo e dois valores
        assert ws.cell(2, 3).value == "Reconciliação — resumo"
        assert ws.cell(3, 3).value == "Reconciliação — valor observado"
        assert ws.cell(3, 21).value == "154.23"
        assert ws.cell(4, 21).value == "1.00"
        assert len(ws.cell(3, 23).value) == 64
    finally:
        wb.close()
    assert exported["exported_financial_reconciliation"] == 3
    service._cross_validation_service.execute_with_report.assert_called_once()
