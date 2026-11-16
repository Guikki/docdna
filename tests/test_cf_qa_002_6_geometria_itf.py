"""CF-QA 002.6 — associação espacial com ITF; cenários sintéticos.

Arquivo INDEPENDENTE: não importa funções de outros módulos de teste.
Salvar em tests/test_cf_qa_002_6_geometria_itf.py.

Os testes NÃO demonstram, por si sós, que as omissões nos PDFs reais
foram resolvidas. Para isso será necessária uma validação funcional com
os documentos de referência e um teste de aceite na planilha exportada.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.detectors.barcode_numeric_line_detector import (
    BarcodeNumericLineDetector,
)
from app.domain.rules.numeric_line_validator import NumericLineValidator


INVALID_CODE = "PAYMENT_LINE_INVALID_STRUCTURE"
VALIDATOR = NumericLineValidator()


def _validation(digits: str):
    return VALIDATOR.validate(
        SimpleNamespace(line_index=1, normalized_content=digits)
    )


def _location(
    digits: str,
    *,
    matched: str | None = None,
    left: int = 210,
    top: int = 105,
):
    return SimpleNamespace(
        line_index=1,
        page_number=1,
        matched_content=matched if matched is not None else digits,
        located=True,
        confidence=0.99,
        left=left,
        top=top,
        width=370,
        height=20,
    )


def _box(text: str, *, left: int = 20, top: int = 102):
    return SimpleNamespace(
        text=text,
        page_number=1,
        left=left,
        top=top,
        width=165,
        height=22,
        confidence=0.99,
    )


def _itf(content: str, *, y: int = 58, x: int = 105, page: int = 1):
    return SimpleNamespace(
        barcode_index=7,
        page_number=page,
        content=content,
        format="ITF",
        location=SimpleNamespace(
            page_number=page,
            bounding_box=SimpleNamespace(x=x, y=y, width=240, height=52),
        ),
    )


def _ctx(
    digits: str,
    *,
    bars: list | None = None,
    loc=None,
):
    return SimpleNamespace(
        numeric_line_validations=[_validation(digits)],
        numeric_line_locations=[
            loc if loc is not None else _location(digits)
        ],
        # Rótulo cadastral propositalmente não autoriza a evidência;
        # o teste precisa comprovar o comportamento da geometria do ITF.
        ocr_text_boxes=[_box("Conta do cliente")],
        barcodes=(
            bars if bars is not None else [_itf("8468" + "0" * 40)]
        ),
    )


def _codes(context) -> list[str]:
    return [
        evidence.code
        for evidence in BarcodeNumericLineDetector().analyze(context)
    ]


@pytest.mark.parametrize(
    "candidate",
    [
        "835271604927490638172754217954806473963407251884",
        "583914726405271638950427846205371694394781620538",
        "5468" + "1" * 44,
    ],
)
def test_linha_48_invalida_ao_lado_de_itf_real_gera_alerta_sem_rotulo(candidate):
    evidence = [
        item
        for item in BarcodeNumericLineDetector().analyze(_ctx(candidate))
        if item.code == INVALID_CODE
    ]
    assert len(evidence) == 1
    assert "proximidade espacial" in evidence[0].description
    assert "não comprova fraude" in evidence[0].description
    assert evidence[0].confidence <= 0.85


def test_mesma_pagina_sem_localizacao_itf_nao_basta():
    code = "835" + "1" * 45
    barcode = SimpleNamespace(
        barcode_index=1,
        page_number=1,
        content="8468" + "0" * 40,
        format="ITF",
    )
    assert INVALID_CODE not in _codes(_ctx(code, bars=[barcode]))


def test_itf_distante_nao_vincula_linha():
    code = "835" + "1" * 45
    assert INVALID_CODE not in _codes(
        _ctx(code, bars=[_itf("8468" + "0" * 40, y=590)])
    )


def test_sem_sobreposicao_horizontal_nao_vincula():
    code = "835" + "1" * 45
    assert INVALID_CODE not in _codes(
        _ctx(code, bars=[_itf("8468" + "0" * 40, x=800)])
    )


def test_dois_itfs_diferentes_proximos_mantem_inconclusivo():
    code = "835" + "1" * 45
    bars = [
        _itf("8468" + "0" * 40),
        _itf("8468" + "1" * 40, x=110),
    ]
    assert INVALID_CODE not in _codes(_ctx(code, bars=bars))


def test_itf_em_outra_pagina_nao_vincula():
    code = "835" + "1" * 45
    assert INVALID_CODE not in _codes(
        _ctx(code, bars=[_itf("8468" + "0" * 40, page=2)])
    )


def test_linha_com_conteudo_visual_parcial_nao_gera_alerta():
    code = "583914726405271638950427846205371694394781620538"
    location = _location(code, matched=code[:-1])
    assert INVALID_CODE not in _codes(_ctx(code, loc=location))


def test_47_digitos_ao_lado_de_itf_arrecadacao_sem_rotulo_nao_basta():
    code = "7" * 47
    assert INVALID_CODE not in _codes(_ctx(code))
