"""CF-QA 002.2 — integração não destrutiva do núcleo financeiro no upload.

Não lê PDFs reais, não depende de exemplos do lote de 656 documentos e não
substitui os testes completos dos leitores: isola a integração do use case.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest

import app.domain.use_cases.upload_document_use_case as usecase_module


def _modulo_10(digits: str) -> int:
    total = 0
    multiplier = 2
    for digit in reversed(digits):
        product = int(digit) * multiplier
        total += product // 10 + product % 10
        multiplier = 1 if multiplier == 2 else 2
    return (-total) % 10


def _barcode_arrecadacao(centavos: int) -> str:
    """Código válido de arrecadação com valor variável e sem marca comercial."""
    assert 0 < centavos <= 99_999_999_999
    body = f"826{centavos:011d}1234" + "1234567890123456789012345"
    assert len(body) == 43
    barcode = body[:3] + str(_modulo_10(body)) + body[3:]
    assert len(barcode) == 44
    return barcode


def _preparar_ambiente(monkeypatch, tmp_path, *, codigo: str | None):
    barcodes = [] if codigo is None else [
        SimpleNamespace(
            barcode_index=3,
            page_number=2,
            format="ITF",
            content=codigo,
        )
    ]
    context = SimpleNamespace(
        pdf_info=None,
        native_text=SimpleNamespace(content=""),
        ocr=SimpleNamespace(content=""),
        images=[],
        image_fingerprints=[],
        qrcode_fingerprints=[],
        normalized_document=None,
        visual_concealment_analysis=None,
        visual_concealment_locations=[],
        barcodes=barcodes,
        printed_numeric_lines=[],
        numeric_line_validations=[],
        numeric_line_locations=[],
        ocr_text_boxes=[],
    )
    monkeypatch.setattr(
        usecase_module,
        "settings",
        SimpleNamespace(UPLOADS_DIR=tmp_path),
    )
    monkeypatch.setattr(
        usecase_module,
        "AnalysisContextBuilder",
        lambda: SimpleNamespace(build=lambda _document: context, performance_report=None),
    )
    monkeypatch.setattr(
        usecase_module,
        "BarcodePresenceDetector",
        lambda: SimpleNamespace(analyze=lambda _context: []),
    )
    monkeypatch.setattr(
        usecase_module,
        "BarcodeNumericLineDetector",
        lambda: SimpleNamespace(
            compare=lambda _context: [],
            analyze=lambda _context: [],
        ),
    )
    monkeypatch.setattr(
        usecase_module,
        "PromptInjectionAnalysisService",
        lambda: SimpleNamespace(analyze=lambda **_kwargs: None),
    )
    monkeypatch.setattr(
        usecase_module,
        "PromptInjectionVisualEvidenceBuilder",
        lambda: SimpleNamespace(),
    )
    return context


@pytest.mark.parametrize("centavos", [1, 12_340, 9_876_543])
def test_upload_preserva_valor_e_proveniencia_sem_mudar_risco(
    monkeypatch, tmp_path, centavos: int,
):
    codigo = _barcode_arrecadacao(centavos)
    _preparar_ambiente(monkeypatch, tmp_path, codigo=codigo)

    arquivo = SimpleNamespace(
        filename="documento_generico.pdf",
        content_type="application/pdf",
        file=BytesIO(b"%PDF-1.4 teste isolado de integracao"),
    )
    analise = usecase_module.UploadDocumentUseCase().execute(arquivo)

    financeiro = analise["financial_reconciliation"]
    assert financeiro["status"] == "INCONCLUSIVE"  # Apenas ITF, sem comparação.
    assert len(financeiro["values"]) == 1
    [valor] = financeiro["values"]
    assert valor["source"] == "ITF"
    assert valor["amount"] == str(Decimal(centavos) / Decimal(100))
    assert isinstance(valor["amount"], str)  # JSON sem perda via Decimal -> float.
    assert valor["page_number"] == 2
    assert valor["barcode_index"] == 3
    assert valor["raw_content"] == codigo
    assert "FEBRABAN" in valor["provenance"]

    assert analise["evidences"] == []
    assert analise["barcode_line_comparisons"] == []
    assert "financial_reconciliation" in analise["performance"]["stages"]
    assert analise["sha256"]
    json.dumps(financeiro)


def test_upload_sem_dados_financeiros_continua_evidencia_inconclusiva(
    monkeypatch, tmp_path,
):
    _preparar_ambiente(monkeypatch, tmp_path, codigo=None)
    arquivo = SimpleNamespace(
        filename="documento_sem_pagamento.pdf",
        content_type="application/pdf",
        file=BytesIO(b"%PDF-1.4 teste isolado de integracao"),
    )
    analise = usecase_module.UploadDocumentUseCase().execute(arquivo)
    financeiro = analise["financial_reconciliation"]
    assert financeiro["status"] == "INCONCLUSIVE"
    assert financeiro["values"] == []
    assert analise["evidences"] == []
