"""CF-QA 003.5 — OCR localizado + reconciliação de três fontes.

Testes generalistas: não utilizam valores, titulares ou nomes de operadoras
extraídos de um único laudo. O vínculo entre cobranças permanece PENDENTE.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.services.financial_reconciliation_service import (
    FinancialReconciliationService,
    FinancialReconciliationStatus,
)
from app.domain.use_cases.upload_document_use_case import UploadDocumentUseCase


def _itf(centavos: int, *, pagina: int = 1, indice: int = 1, livre: str = "1234567890123456789012345"):
    body = f"846{centavos:011d}1234{livre}"
    assert len(body) == 43
    dv = FinancialReconciliationService._modulo_10(body)
    return SimpleNamespace(
        content=body[:3]+str(dv)+body[3:], format="ITF",
        barcode_index=indice, page_number=pagina,
    )


def _tlv(tag: str, val: str) -> str:
    assert len(val.encode('utf-8')) < 100
    return f"{tag}{len(val.encode('utf-8')):02d}{val}"


def _pix(valor: str, *, pagina: int = 1, indice: int = 2):
    payload = "".join((
        _tlv("00", "01"),
        _tlv("26", _tlv("00", "br.gov.bcb.pix")+_tlv("01", "chave-teste")),
        _tlv("53", "986"),
        _tlv("54", valor),
        _tlv("58", "BR"),
        _tlv("59", "TESTE"),
        _tlv("60", "SALVADOR"),
    )) + "6304"
    payload += f"{FinancialReconciliationService._crc16_ccitt(payload.encode('utf-8')):04X}"
    return SimpleNamespace(
        content=payload, format="QRCode", barcode_index=indice, page_number=pagina,
    )


def _box(text: str, *, page: int = 1, x: int = 50, y: int = 100,
         w: int = 200, h: int = 20, confidence: float = 95):
    return SimpleNamespace(
        text=text, page_number=page, left=x, top=y,
        width=w, height=h, confidence=confidence,
    )


def _result(*, barcodes=(), boxes=(), native="", ocr=""):
    return FinancialReconciliationService().reconcile(
        barcodes=barcodes,
        native_text=SimpleNamespace(content=native),
        ocr=SimpleNamespace(content=ocr),
        ocr_text_boxes=boxes,
    )


def _printed(result):
    return [v for v in result.values if v.source == "PRINTED"]


def test_tres_fontes_reais_com_valores_distintos_sinalizam_revisao_sem_fraude():
    result = _result(
        barcodes=[_itf(83_915), _pix("1.50")],
        boxes=[_box("Total a pagar: R$ 219,40")],
    )
    assert result.status == FinancialReconciliationStatus.REVIEW_REQUIRED
    assert [(v.source, v.amount) for v in result.values] == [
        ("ITF", Decimal("839.15")),
        ("PIX", Decimal("1.50")),
        ("PRINTED", Decimal("219.40")),
    ]
    [comparison] = result.comparisons
    assert comparison.relation == "DIFFERENT_VALUES"
    assert comparison.sources == ("ITF", "PIX", "PRINTED")
    assert comparison.linkage == "SAME_PAGE_UNCONFIRMED"
    assert "fraude" not in result.message.lower() or "não" in result.message.lower()
    assert "não estão demonstradas" in result.message.lower()


def test_tres_fontes_iguais_nao_geram_falso_alerta():
    result = _result(
        barcodes=[_itf(4_983), _pix("49.83")],
        boxes=[_box("Valor a pagar: R$ 49,83")],
    )
    assert result.status == FinancialReconciliationStatus.CONSISTENT
    assert [c.relation for c in result.comparisons] == ["EQUAL_VALUES"]


def test_total_impresso_diferente_itf_pix_iguais_gera_triagem_com_vinculo_pendente():
    result = _result(
        barcodes=[_itf(4_983), _pix("49.83")],
        boxes=[_box("Valor a pagar: R$ 48,83")],
    )
    assert result.status == FinancialReconciliationStatus.REVIEW_REQUIRED
    assert "mesma cobrança" in result.message


def test_total_em_caixa_ocr_isolada_mantem_pagina_e_geometria():
    [value] = _printed(_result(boxes=[_box("Total devido R$ 78,90", page=3, x=130, y=90)]))
    assert value.page_number == 3
    assert (value.left, value.top, value.width, value.height) == (130, 90, 200, 20)
    assert value.confidence == 95
    assert value.provenance == "OCR_TEXT_BOX"


def test_rotulo_e_valor_em_caixas_ocr_separadas_mesma_linha():
    result = _result(boxes=[
        _box("Valor a pagar", x=100, y=250, w=150),
        _box("R$ 2.013,07", x=270, y=251, w=110),
    ])
    [value] = _printed(result)
    assert value.amount == Decimal("2013.07")
    assert value.page_number == 1
    assert value.provenance == "OCR_TEXT_BOX_PAIR"
    assert value.left == 100 and value.width == 280


def test_rotulo_e_valor_em_caixas_ocr_verticalmente_vizinhas():
    result = _result(boxes=[
        _box("Total a pagar", x=110, y=120, w=140),
        _box("135,29", x=120, y=145, w=90),
    ])
    assert [v.amount for v in _printed(result)] == [Decimal("135.29")]


def test_caixas_de_paginas_diferentes_nunca_sao_unidas():
    result = _result(boxes=[
        _box("Valor a pagar", page=1, x=100, y=250),
        _box("R$ 280,21", page=2, x=320, y=250),
    ])
    assert _printed(result) == []


def test_mais_de_um_preco_proximo_e_ambiguo_e_nao_e_escolhido():
    result = _result(boxes=[
        _box("Total a pagar", x=100, y=250, w=130),
        _box("R$ 82,00", x=250, y=250, w=85),
        _box("R$ 73,00", x=350, y=250, w=85),
    ])
    assert _printed(result) == []


def test_texto_agregado_sem_geometria_nao_recebe_pagina():
    result = _result(native="Total da fatura: R$ 700,51")
    [value] = _printed(result)
    assert value.page_number is None
    assert value.left is None
    assert result.comparisons == []


def test_ocr_agregado_duplicado_nao_gera_segundo_valor_nao_localizado():
    result = _result(
        boxes=[_box("Total a pagar: R$ 199,71")],
        ocr="Total a pagar: R$ 199,71",
    )
    assert len(_printed(result)) == 1
    assert _printed(result)[0].page_number == 1


def test_ocr_de_baixa_confianca_e_preservado_mas_nao_funda_triada():
    result = _result(
        barcodes=[_itf(6_800), _pix("68.00")],
        boxes=[_box("Total a pagar: R$ 900,00", confidence=29)],
    )
    assert len(_printed(result)) == 1
    assert _printed(result)[0].confidence == 29
    assert result.status == FinancialReconciliationStatus.CONSISTENT
    assert all("PRINTED" not in c.sources for c in result.comparisons)


def test_multiplos_itfs_distintos_na_mesma_pagina_nao_sao_pareados_ao_acaso():
    result = _result(
        barcodes=[
            _itf(4_001, indice=1, livre="1" * 25),
            _itf(4_002, indice=3, livre="2" * 25),
            _pix("10.00", indice=2),
        ],
        boxes=[_box("Total a pagar: R$ 20,00")],
    )
    assert result.status == FinancialReconciliationStatus.INCONCLUSIVE
    assert result.comparisons == []


def test_moeda_sem_rotulo_nunca_vira_total_impresso():
    result = _result(
        native="Plano R$ 70,00. Desconto R$ 20,00.",
        boxes=[_box("R$ 50,00")],
    )
    assert _printed(result) == []


def test_itf_curto_e_preservado_sem_virar_valor_financeiro():
    result = _result(barcodes=[SimpleNamespace(
        content="00104360", format="ITF", page_number=1, barcode_index=1,
    )])
    assert not any(v.source == "ITF" for v in result.values)
    assert result.status == FinancialReconciliationStatus.INCONCLUSIVE


def test_resultado_financeiro_e_serializado_sem_floats_de_moeda():
    result = _result(
        barcodes=[_itf(81_349), _pix("1.79")],
        boxes=[_box("Total a pagar: R$ 153,60", x=45, y=80)],
    )
    serialized = UploadDocumentUseCase._serialize_financial_reconciliation(result)
    assert serialized["status"] == "REVIEW_REQUIRED"
    assert len(serialized["values"]) == 3
    assert serialized["values"][2]["page_number"] == 1
    assert serialized["values"][2]["left"] == 45
    assert serialized["comparisons"][0]["linkage"] == "SAME_PAGE_UNCONFIRMED"
    assert serialized["comparisons"][0]["amounts"] == ["813.49", "1.79", "153.60"]
    assert all(type(v["amount"]) is str for v in serialized["values"])


def test_total_impresso_inconclusivo_sem_itf_pix_nunca_muda_risco():
    result = _result(boxes=[_box("Valor a pagar R$ 19,90")])
    assert result.status == FinancialReconciliationStatus.INCONCLUSIVE
    assert result.comparisons == []


def test_divergencia_pix_itf_antiga_continua_prioritaria_sem_total_impresso():
    result = _result(barcodes=[_itf(15_000), _pix("10.00")])
    assert result.status == FinancialReconciliationStatus.REVIEW_REQUIRED
    assert len(result.comparisons) == 1
    assert result.comparisons[0].sources == ("ITF", "PIX")


def test_rotulo_e_valor_na_mesma_caixa_em_linhas_diferentes():
    result = _result(boxes=[_box("Total a pagar\nR$ 713,05")])
    assert [v.amount for v in _printed(result)] == [Decimal("713.05")]


def test_ocr_com_caractere_confundido_nao_inventa_total():
    result = _result(boxes=[_box("Total a pagar R$ 1O9,90")])
    assert _printed(result) == []


def test_upload_realmente_encaminha_caixas_ocr_ao_servico(monkeypatch, tmp_path):
    """Integração do use case sem PDF externo nem armazenamento em produção."""
    from io import BytesIO
    import app.domain.use_cases.upload_document_use_case as upload_module

    context = SimpleNamespace(
        pdf_info=None,
        native_text=SimpleNamespace(content=""),
        ocr=SimpleNamespace(content=""),
        ocr_text_boxes=[_box("Total a pagar: R$ 219,40", page=2)],
        images=[], image_fingerprints=[], qrcode_fingerprints=[],
        normalized_document=None, visual_concealment_analysis=None,
        visual_concealment_locations=[],
        barcodes=[_itf(83_915, pagina=2), _pix("1.50", pagina=2)],
        printed_numeric_lines=[], numeric_line_validations=[],
        numeric_line_locations=[],
    )
    monkeypatch.setattr(upload_module, "settings", SimpleNamespace(UPLOADS_DIR=tmp_path))
    monkeypatch.setattr(upload_module, "AnalysisContextBuilder", lambda: SimpleNamespace(
        build=lambda _document: context, performance_report=None,
    ))
    monkeypatch.setattr(upload_module, "BarcodePresenceDetector", lambda: SimpleNamespace(
        analyze=lambda _context: [],
    ))
    monkeypatch.setattr(upload_module, "BarcodeNumericLineDetector", lambda: SimpleNamespace(
        compare=lambda _context: [], analyze=lambda _context: [],
    ))
    monkeypatch.setattr(upload_module, "PromptInjectionAnalysisService", lambda: SimpleNamespace(
        analyze=lambda **_kwargs: None,
    ))
    monkeypatch.setattr(upload_module, "PromptInjectionVisualEvidenceBuilder", lambda: SimpleNamespace())
    archive = SimpleNamespace(
        filename="amostra_generica.pdf", content_type="application/pdf",
        file=BytesIO(b"%PDF-1.4 teste isolado"),
    )
    output = upload_module.UploadDocumentUseCase().execute(archive)
    result = output["financial_reconciliation"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert {x["source"]: x["amount"] for x in result["values"]} == {
        "ITF": "839.15", "PIX": "1.50", "PRINTED": "219.40",
    }
    assert result["values"][2]["page_number"] == 2
    assert result["comparisons"][0]["sources"] == ["ITF", "PIX", "PRINTED"]
    assert output["evidences"] == []
