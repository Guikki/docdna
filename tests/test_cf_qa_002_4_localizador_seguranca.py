"""CF-QA 002.4 — regressões complementares de localização visual.

Os casos são sintéticos e não dependem de empresa, processo ou fatura real.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.services.numeric_line_visual_evidence_builder import (
    NumericLineVisualEvidenceBuilder,
)


def _box(text, *, page=1, left=10, top=100):
    return SimpleNamespace(
        text=text,
        page_number=page,
        left=left,
        top=top,
        width=max(15, len(text) * 8),
        height=20,
        confidence=0.98,
    )


def _locate(monkeypatch, boxes, target):
    builder = NumericLineVisualEvidenceBuilder()
    calls = []

    def _render(**kwargs):
        calls.append(kwargs)
        return Path('original.png'), Path('anotada.png')

    monkeypatch.setattr(builder, '_render_annotated_page', _render)
    result = builder._locate_line(
        pdf_path='sintetico.pdf',
        line=SimpleNamespace(line_index=1, normalized_content=target),
        boxes=boxes,
        output_dir=Path('.'),
    )
    return result, calls


def test_uma_ocorrencia_dividida_em_quatro_caixas_permanece_localizavel(monkeypatch):
    digits = '8' + '6' * 47
    boxes = [
        _box(digits[i:i+12], left=10 + i*9) for i in range(0, 48, 12)
    ]
    result, calls = _locate(monkeypatch, boxes, digits)
    assert result.located is True
    assert result.page_number == 1
    assert result.matched_content == digits
    assert len(calls) == 1


def test_texto_duplicado_dentro_da_mesma_caixa_e_ambiguo(monkeypatch):
    digits = '8' + '7' * 47
    result, calls = _locate(monkeypatch, [_box(digits + digits)], digits)
    assert result.located is False
    assert result.page_number is None
    assert 'ambígua' in result.message.lower()
    assert calls == []


def test_caixas_ocr_duplicadas_com_mesma_geometria_nao_dao_certeza(monkeypatch):
    digits = '8' + '3' * 47
    boxes = [_box(digits), _box(digits)]
    result, calls = _locate(monkeypatch, boxes, digits)
    assert result.located is False
    assert result.page_number is None
    assert calls == []


def test_a_ordem_das_paginas_nao_desfaz_a_ambiguidade(monkeypatch):
    digits = '8' + '2' * 47
    boxes = [_box(digits, page=4), _box(digits, page=1)]
    result, calls = _locate(monkeypatch, boxes, digits)
    assert result.located is False
    assert result.page_number is None
    assert calls == []


def test_candidato_e_seu_prefixo_mesma_caixa_nao_contam_como_dois_lugares(monkeypatch):
    digits = '8' + '4' * 47
    result, calls = _locate(monkeypatch, [_box(digits, page=2)], digits)
    assert result.located is True
    assert result.page_number == 2
    assert len(calls) == 1


def test_documento_sem_ocorrencia_nao_gera_imagem_anotada(monkeypatch):
    digits = '8' + '5' * 47
    result, calls = _locate(monkeypatch, [_box('9' * 48, page=3)], digits)
    assert result.located is False
    assert result.page_number is None
    assert calls == []


@pytest.mark.parametrize("first_digit", ["0", "4", "5", "9"])
def test_correspondencia_integral_de_48_digitos_precede_prefixo_de_47(monkeypatch, first_digit):
    digits = first_digit + "1234567890" * 4 + "1234567"
    boxes = [_box(digits[i:i + 12], left=10 + i * 9) for i in range(0, 48, 12)]
    for box in boxes:
        box.confidence = 42.25
    result, calls = _locate(monkeypatch, boxes, digits)
    assert result.located is True
    assert result.matched_content == digits
    assert result.confidence == 42.25
    assert "trecho interno" not in result.message
    assert len(calls) == 1


def test_preferencia_integral_nao_ignora_ocorrencia_em_outra_pagina(monkeypatch):
    digits = "4" + "1234567890" * 4 + "1234567"
    result, calls = _locate(monkeypatch, [_box(digits, page=1), _box(digits, page=2)], digits)
    assert result.located is False
    assert calls == []


def test_subsequencia_continua_disponivel_quando_conteudo_integral_nao_esta_no_ocr(monkeypatch):
    inner = "8" + "1234567890" * 4 + "1234567"
    result, calls = _locate(monkeypatch, [_box(inner)], "99" + inner)
    assert result.located is True
    assert result.matched_content == inner
    assert "trecho interno" in result.message
    assert len(calls) == 1
