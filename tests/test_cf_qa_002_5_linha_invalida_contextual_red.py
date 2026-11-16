"""CF-QA 002.5 — RED: invalidez estrutural de linha de pagamento contextualizada.

Objetivo: permitir um apontamento próprio para linha efetivamente impressa
como meio de pagamento, mas estruturalmente inválida, sem inflar
BARCODE_LINE_MISMATCH e sem sinalizar números aleatórios do PDF/OCR.

Apenas testes; NÃO muda o código de produção. Sintéticos, sem faturas Vivo.

Contrato mínimo de segurança para o futuro GREEN:
- formato de 47 ou 48 dígitos + invalidez técnica verificável;
- localização visual única e confiável;
- rótulo próximo, na MESMA PÁGINA, vinculando a sequência à função
  de linha digitável de pagamento;
- sem inferir divergência com ITF apenas pela mesma página;
- sem promover texto OCR fraco, números soltos ou referências ambíguas.

Resultado RED esperado com o detector atual: testes de indicação positiva
falham por ausência de PAYMENT_LINE_INVALID_STRUCTURE; controles negativos
permanecem aprovados.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.detectors.barcode_numeric_line_detector import (
    BarcodeNumericLineDetector,
)
from app.domain.models.barcode_line_comparison import (
    BarcodeLineComparisonStatus,
)
from app.domain.models.numeric_line_validation import (
    NumericLineValidationStatus,
)
from app.domain.rules.numeric_line_converter import NumericLineConverter
from app.domain.rules.numeric_line_validator import NumericLineValidator


INVALID_LINE_EVIDENCE = "PAYMENT_LINE_INVALID_STRUCTURE"
VALIDATOR = NumericLineValidator()


def _collection_barcode() -> str:
    """ITF sintético de arrecadação; não pertence a fatura real."""
    return "8468" + "00000007045" + "0034" + "7654321098765432109876543"


def _valid_collection_line() -> str:
    barcode = _collection_barcode()
    assert len(barcode) == 44
    return "".join(
        barcode[start:start + 11]
        + str(VALIDATOR._modulo_10(barcode[start:start + 11]))
        for start in (0, 11, 22, 33)
    )


def _invalid_collection_dv() -> str:
    valid_line = _valid_collection_line()
    assert len(valid_line) == 48
    different_dv = str((int(valid_line[11]) + 1) % 10)
    return valid_line[:11] + different_dv + valid_line[12:]


def _invalid_bank_dv() -> str:
    fields = ("001905009", "1234567890", "8576302198")
    valid_line = (
        fields[0] + str(VALIDATOR._modulo_10(fields[0]))
        + fields[1] + str(VALIDATOR._modulo_10(fields[1]))
        + fields[2] + str(VALIDATOR._modulo_10(fields[2]))
        + "123456789012345"
    )
    assert len(valid_line) == 47
    wrong_dv = str((int(valid_line[9]) + 1) % 10)
    return valid_line[:9] + wrong_dv + valid_line[10:]


def _validation(digits: str, index: int = 1):
    item = SimpleNamespace(line_index=index, normalized_content=digits)
    return VALIDATOR.validate(item)


def _location(
    digits: str,
    *,
    index: int = 1,
    page: int | None = 1,
    located: bool = True,
    confidence: float = 0.99,
    left: int = 210,
    top: int = 105,
    matched: str | None = None,
):
    return SimpleNamespace(
        line_index=index,
        page_number=page if located else None,
        matched_content=matched if matched is not None else digits,
        located=located,
        confidence=confidence if located else None,
        left=left if located else None,
        top=top if located else None,
        width=370 if located else None,
        height=20 if located else None,
    )


def _box(
    text: str = "Linha digitável:",
    *,
    page: int = 1,
    left: int = 25,
    top: int = 102,
    width: int = 165,
    height: int = 22,
    confidence: float = 0.99,
):
    return SimpleNamespace(
        text=text,
        page_number=page,
        left=left,
        top=top,
        width=width,
        height=height,
        confidence=confidence,
    )


def _barcode(*, page=1, content=None):
    return SimpleNamespace(
        page_number=page,
        barcode_index=4,
        content=content or _collection_barcode(),
        format="ITF",
    )


def _context(
    digits: str,
    *,
    label_boxes=None,
    location=None,
    barcodes=None,
):
    return SimpleNamespace(
        numeric_line_validations=[_validation(digits)],
        numeric_line_locations=[
            location if location is not None else _location(digits)
        ],
        ocr_text_boxes=label_boxes if label_boxes is not None else [_box()],
        barcodes=barcodes if barcodes is not None else [_barcode()],
    )


def _codes(context):
    return [evidence.code for evidence in BarcodeNumericLineDetector().analyze(context)]


# Positivos: uma linha de pagamento CONTEXTUALIZADA pode ser inválida,
# mesmo que o validador anterior a tenha deixado inconclusiva.
@pytest.mark.parametrize(
    "digits, expected_validator_status",
    [
        (_invalid_collection_dv(), NumericLineValidationStatus.INVALID),
        ("845" + "1" * 45, NumericLineValidationStatus.INCONCLUSIVE),
        ("5" + _valid_collection_line()[1:], NumericLineValidationStatus.INCONCLUSIVE),
        (_invalid_bank_dv(), NumericLineValidationStatus.INVALID),
    ],
)
def test_red_linha_identificada_visualmente_invalida_gera_apontamento_proprio(
    digits, expected_validator_status,
):
    assert _validation(digits).status == expected_validator_status
    context = _context(digits)
    assert INVALID_LINE_EVIDENCE in _codes(context)
    assert "BARCODE_LINE_MISMATCH" not in _codes(context)


@pytest.mark.parametrize("label", ["Linha digitável:", "Linha para pagamento:"])
def test_red_linha_invalida_com_rotulo_sem_itf_ainda_e_anomalia_de_estrutura(label):
    context = _context(_invalid_collection_dv(), barcodes=[], label_boxes=[_box(text=label)])
    assert INVALID_LINE_EVIDENCE in _codes(context)
    assert "BARCODE_LINE_MISMATCH" not in _codes(context)


def test_red_apontamento_registra_indice_pagina_e_motivo_sem_afirmar_fraude():
    context = _context(_invalid_collection_dv())
    evidence = [
        e for e in BarcodeNumericLineDetector().analyze(context)
        if e.code == INVALID_LINE_EVIDENCE
    ]
    assert len(evidence) == 1
    description = evidence[0].description.lower()
    assert "página 1" in description
    assert "linha" in description
    assert "dígito" in description or "estrutura" in description
    assert "fraude comprovada" not in description


# Negativos: números sem vínculo financeiro comprovável NÃO geram evidência.
def test_controle_candidato_invalido_sem_rotulo_financeiro_nao_gera_alerta():
    context = _context(_invalid_collection_dv(), label_boxes=[])
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_rotulo_cadastral_nao_e_rotulo_de_pagamento():
    context = _context(
        _invalid_collection_dv(),
        label_boxes=[_box(text="Número da conta:")],
    )
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_rotulo_em_pagina_diferente_nao_gera_alerta():
    context = _context(_invalid_collection_dv(), label_boxes=[_box(page=2)])
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_rotulo_muito_distante_na_pagina_nao_gera_alerta():
    context = _context(_invalid_collection_dv(), label_boxes=[_box(top=900)])
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_localizacao_nao_confirmada_nao_gera_alerta():
    digits = _invalid_collection_dv()
    context = _context(digits, location=_location(digits, located=False))
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_ocr_com_baixa_confianca_nao_gera_alerta():
    context = _context(
        _invalid_collection_dv(),
        label_boxes=[_box(confidence=0.30)],
    )
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_localizacao_com_baixa_confianca_nao_gera_alerta():
    digits = _invalid_collection_dv()
    context = _context(
        digits,
        location=_location(digits, confidence=0.35),
    )
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_localizacao_nao_corresponde_ao_candidato_nao_gera_alerta():
    digits = _invalid_collection_dv()
    context = _context(
        digits,
        location=_location(digits, matched="1" * 48),
    )
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_sequencia_binaria_de_50_digitos_nao_gera_alerta():
    context = _context("01" * 25)
    assert INVALID_LINE_EVIDENCE not in _codes(context)


def test_controle_linha_valida_nao_recebe_rotulo_de_invalida():
    valid_line = _valid_collection_line()
    validation = _validation(valid_line)
    assert validation.status == NumericLineValidationStatus.VALID
    assert NumericLineConverter().convert_to_barcode(validation) == _collection_barcode()
    context = _context(valid_line)
    assert INVALID_LINE_EVIDENCE not in _codes(context)
    [comparison] = BarcodeNumericLineDetector().compare(context)
    assert comparison.status == BarcodeLineComparisonStatus.MATCH


def test_controle_linha_invalida_permanece_inconclusiva_na_comparacao_itf():
    context = _context(_invalid_collection_dv())
    [comparison] = BarcodeNumericLineDetector().compare(context)
    assert comparison.status == BarcodeLineComparisonStatus.INCONCLUSIVE
    assert comparison.barcode_index is None


def test_controle_qrcode_numerico_nao_fundamenta_divergencia():
    validation = _validation(_valid_collection_line())
    context = _context(
        _valid_collection_line(),
        barcodes=[SimpleNamespace(
            page_number=1,
            barcode_index=1,
            content=_collection_barcode(),
            format="QRCode",
        )],
    )
    assert validation.status == NumericLineValidationStatus.VALID
    [comparison] = BarcodeNumericLineDetector().compare(context)
    assert comparison.status == BarcodeLineComparisonStatus.INCONCLUSIVE
