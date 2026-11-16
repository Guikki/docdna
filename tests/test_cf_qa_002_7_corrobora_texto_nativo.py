"""CF-QA 002.7: OCR de baixa confianca so e aceito com texto nativo POSICIONADO.

Salvar em tests/test_cf_qa_002_7_corrobora_texto_nativo.py.
Estes testes nao substituem o aceite nos PDFs originais do DocDNA.
"""
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from app.domain.detectors.barcode_numeric_line_detector import BarcodeNumericLineDetector
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.services.native_numeric_line_corrobator import NativeNumericLineCorroborator


LINE = "835271604927490638172754217954806473963407251884"
ITF = "84680000006096900481000112943786092506903643"
INVALID_CODE = "PAYMENT_LINE_INVALID_STRUCTURE"


def _pdf(tmp_path: Path, *, line=LINE, count=1, pageno=1) -> tuple[str, tuple]:
    path = tmp_path / f"source_{pageno}_{count}.pdf"
    with pymupdf.open() as document:
        for _ in range(pageno):
            document.new_page(width=612, height=792)
        page = document[pageno - 1]
        for i in range(count):
            page.insert_text((90, 766 + i * 12), line, fontsize=7)
        document.save(str(path))
    with pymupdf.open(str(path)) as doc:
        words = doc[pageno - 1].get_text("words")
    native = next(w for w in words if LINE in str(w[4]) or line in str(w[4]))
    return str(path), (native[0], native[1], native[2], native[3])


def _args(path, rect, *, expected=LINE, page=1, dx=0, dy=0):
    x0, y0, x1, y1 = rect
    return dict(
        pdf_path=path,
        page_number=page,
        expected_digits=expected,
        ocr_left=x0 * 2 + dx,
        ocr_top=y0 * 2 + dy,
        ocr_width=(x1 - x0) * 2,
        ocr_height=(y1 - y0) * 2,
    )


def _context(path, rect, *, digits=LINE, conf=42.25, visual=None, barcode=True):
    val = NumericLineValidator().validate(SimpleNamespace(line_index=1, normalized_content=digits))
    x0, y0, x1, y1 = rect
    location = SimpleNamespace(
        line_index=1, located=True, page_number=1,
        matched_content=digits if visual is None else visual,
        confidence=conf, left=x0 * 2, top=y0 * 2,
        width=(x1 - x0) * 2, height=(y1 - y0) * 2,
    )
    # ITF imediatamente abaixo da linha, em unidades PDF.
    barcode_obj = SimpleNamespace(
        barcode_index=2, page_number=1, format="ITF", content=ITF,
        location=SimpleNamespace(page_number=1, bounding_box=SimpleNamespace(
            x=x0, y=y1 + 3, width=x1 - x0, height=30,
        )),
    )
    return SimpleNamespace(
        saved_path=path,
        numeric_line_validations=[val], numeric_line_locations=[location],
        ocr_text_boxes=[], barcodes=[barcode_obj] if barcode else [],
    )


def _codes(context):
    return [e.code for e in BarcodeNumericLineDetector().analyze(context)]


def test_native_pdf_confirma_integralmente_linha_com_baixa_confianca_ocr(tmp_path):
    path, rect = _pdf(tmp_path)
    assert NativeNumericLineCorroborator().confirms(**_args(path, rect))
    evidence = [e for e in BarcodeNumericLineDetector().analyze(_context(path, rect)) if e.code == INVALID_CODE]
    assert len(evidence) == 1
    assert "texto nativo" in evidence[0].description
    assert "42.25/100" in evidence[0].description
    assert evidence[0].confidence <= 0.85


def test_texto_nativo_com_um_digito_diferente_nao_autoriza_alerta(tmp_path):
    path, rect = _pdf(tmp_path, line=LINE[:-1] + "3")
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect))
    assert INVALID_CODE not in _codes(_context(path, rect))


def test_texto_nativo_em_pagina_diferente_nao_autoriza_alerta(tmp_path):
    path, rect = _pdf(tmp_path, pageno=2)
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect, page=1))


def test_texto_nativo_distante_nao_autoriza_alerta(tmp_path):
    path, rect = _pdf(tmp_path)
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect, dy=300))
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect, dx=400))


def test_conteudo_visual_incompleto_nao_autoriza_alerta_mesmo_com_nativo(tmp_path):
    path, rect = _pdf(tmp_path)
    assert INVALID_CODE not in _codes(_context(path, rect, visual=LINE[:-1]))


def test_falta_de_itf_nao_autoriza_alerta_sem_rotulo(tmp_path):
    path, rect = _pdf(tmp_path)
    assert INVALID_CODE not in _codes(_context(path, rect, barcode=False))


def test_ocr_com_baixa_confianca_sem_pdf_nao_autoriza_alerta():
    fake_rect = (90, 760, 350, 770)
    assert INVALID_CODE not in _codes(_context("/nao_existe.pdf", fake_rect))


def test_ocr_confiavel_continua_funcionando_sem_texto_nativo(tmp_path):
    fake_rect = (90, 760, 350, 770)
    # Nesta condicao antiga, a confianca visual 0.99 permite a via geometrica.
    assert INVALID_CODE in _codes(_context("/nao_existe.pdf", fake_rect, conf=99))


def test_arquivo_sem_pagina_ou_sem_digitos_nao_e_corroboraçao(tmp_path):
    path, rect = _pdf(tmp_path)
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect, page=99))
    assert not NativeNumericLineCorroborator().confirms(**_args(path, rect, expected="abc"))


def test_texto_nativo_em_quatro_blocos_de_doze_digitos(tmp_path):
    """Layout de arrecadacao comum: quatro grupos numericos na mesma linha."""
    path = tmp_path / "quatro_blocos.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        for i in range(4):
            page.insert_text((90 + 65 * i, 766), LINE[12 * i:12 * (i + 1)], fontsize=7)
        document.save(str(path))
    with pymupdf.open(str(path)) as document:
        words = document[0].get_text("words")
    assert len(words) == 4
    rect = (
        min(w[0] for w in words), min(w[1] for w in words),
        max(w[2] for w in words), max(w[3] for w in words),
    )
    assert NativeNumericLineCorroborator().confirms(**_args(str(path), rect))


def test_fragmentos_numericos_distantes_nao_sao_juntados(tmp_path):
    path = tmp_path / "fragmentos_distantes.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=700, height=792)
        for i in range(4):
            page.insert_text((30 + 165 * i, 766), LINE[12 * i:12 * (i + 1)], fontsize=7)
        document.save(str(path))
    with pymupdf.open(str(path)) as document:
        words = document[0].get_text("words")
    rect = (
        min(w[0] for w in words), min(w[1] for w in words),
        max(w[2] for w in words), max(w[3] for w in words),
    )
    assert not NativeNumericLineCorroborator().confirms(**_args(str(path), rect))
