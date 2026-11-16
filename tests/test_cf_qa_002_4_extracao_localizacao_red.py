"""CF-QA 002.4 — RED: confiabilidade de candidatos e localizações financeiras.

Regressões generalizáveis, SEM exemplos de empresa, processo ou fatura real.
Antes de criar alertas para linhas estruturalmente inválidas, assegurar que
um leitor não invente candidatos e um localizador não invente proveniência.

Esperado com arquivos de referência de 2026-10/08:
  6 testes de controle passam; 4 testes RED falham.
Resultados do projeto atual podem diferir se esses erros já foram corrigidos.
"""
from pathlib import Path
from types import SimpleNamespace

from app.domain.readers.printed_numeric_line_reader import (
    PrintedNumericLineReader,
)
from app.domain.services.numeric_line_visual_evidence_builder import (
    NumericLineVisualEvidenceBuilder,
)
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.models.numeric_line_validation import NumericLineValidationStatus


def _box(text: str, *, page: int = 1, left: int = 20, top: int = 100):
    return SimpleNamespace(
        text=text,
        page_number=page,
        left=left,
        top=top,
        width=max(20, len(text) * 8),
        height=22,
        confidence=0.99,
    )


def _candidate(digits: str, line_index: int = 1):
    return SimpleNamespace(
        line_index=line_index,
        raw_content=digits,
        normalized_content=digits,
        digit_count=len(digits),
        source="ocr",
    )


def _locate(monkeypatch, digits, boxes):
    builder = NumericLineVisualEvidenceBuilder()
    monkeypatch.setattr(
        builder,
        "_render_annotated_page",
        lambda **kwargs: (Path("source.png"), Path("annotated.png")),
    )
    return builder._locate_line(
        pdf_path="documento_sintetico.pdf",
        line=_candidate(digits),
        boxes=boxes,
        output_dir=Path("."),
    )


def test_controle_linha_de_arrecadacao_48_digitos_em_um_campo():
    digits = "8" + "6" * 47
    result = PrintedNumericLineReader()._extract_candidates(digits)
    assert len(result) == 1
    assert result[0][1] == digits


def test_controle_linha_bancaria_47_digitos_em_um_campo():
    digits = "1" + "7" * 46
    result = PrintedNumericLineReader()._extract_candidates(digits)
    assert len(result) == 1
    assert result[0][1] == digits


def test_controle_separadores_horizontais_da_linha_sao_aceitos():
    digits = "8" + "6" * 47
    pretty = " ".join(digits[i:i + 12] for i in range(0, 48, 12))
    result = PrintedNumericLineReader()._extract_candidates(pretty)
    assert len(result) == 1
    assert result[0][1] == digits


def test_controle_linha_nao_localizada_nao_recebe_pagina(monkeypatch):
    digits = "8" + "6" * 47
    result = _locate(monkeypatch, digits, [_box("9" * 48, page=2)])
    assert result.located is False
    assert result.page_number is None


def test_controle_linha_completa_e_unica_tem_localizacao(monkeypatch):
    digits = "8" + "6" * 47
    result = _locate(monkeypatch, digits, [_box(digits, page=3)])
    assert result.located is True
    assert result.page_number == 3
    assert result.matched_content == digits


def test_controle_48_com_referencia_desconhecida_nao_e_validada():
    digits = "835" + "1234567890" * 4 + "12345"
    assert len(digits) == 48
    result = NumericLineValidator().validate(_candidate(digits))
    assert result.status != NumericLineValidationStatus.VALID


def test_red_fluxo_longo_nao_e_fatiado_em_falsas_linhas_de_50():
    digits = "1234567890" * 10
    result = PrintedNumericLineReader()._extract_candidates(digits)
    assert result == [], "100 dígitos contíguos não formam dois pagamentos de 50."


def test_red_duas_linhas_de_48_separadas_por_quebra_nao_se_fundem():
    first = "8" + "6" * 47
    second = "8" + "7" * 47
    result = PrintedNumericLineReader()._extract_candidates(first + "\n" + second)
    assert [item[1] for item in result] == [first, second]


def test_red_numero_repetido_em_paginas_diferentes_nao_escolhe_a_primeira(monkeypatch):
    digits = "8" + "6" * 47
    result = _locate(monkeypatch, digits, [
        _box(digits, page=1),
        _box(digits, page=2),
    ])
    assert result.located is False
    assert result.page_number is None


def test_red_numero_repetido_em_regioes_da_mesma_pagina_e_ambiguo(monkeypatch):
    digits = "8" + "6" * 47
    result = _locate(monkeypatch, digits, [
        _box(digits, page=1, top=100),
        _box(digits, page=1, top=350),
    ])
    assert result.located is False
    assert result.page_number is None
