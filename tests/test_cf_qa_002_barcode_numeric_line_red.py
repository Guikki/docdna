"""Testes RED do CF-QA 002 — vínculo seguro entre linha e código.

Estes testes especificam a política conservadora esperada: só declarar
correspondência ou divergência quando existe evidência para associar
uma linha digitável ao código de pagamento analisado.

Não alteram o comportamento da aplicação. Três cenários devem falhar
no detector atual e um serve como controle positivo.
"""

from types import SimpleNamespace

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

ITF_VIVO = "84680000006096900481000112943786092506903643"
LINHA_VIVO_CORRESPONDENTE = (
    "846800000065096900481001011294378606925069036430"
)


def _linha_validada():
    """Gera uma linha de arrecadação válida conhecida e reproduzível."""
    linha = SimpleNamespace(
        line_index=1,
        normalized_content=LINHA_VIVO_CORRESPONDENTE,
    )
    validacao = NumericLineValidator().validate(linha)
    assert validacao.status == NumericLineValidationStatus.VALID
    assert NumericLineConverter().convert_to_barcode(validacao) == ITF_VIVO
    return validacao


def _codigo(*, conteudo: str, pagina: int, formato: str = "ITF"):
    return SimpleNamespace(
        barcode_index=1,
        page_number=pagina,
        format=formato,
        content=conteudo,
    )


def _contexto(*, codigos, pagina_da_linha: int = 1):
    """Fornece apenas os dados consumidos pelo detector."""
    return SimpleNamespace(
        numeric_line_validations=[_linha_validada()],
        numeric_line_locations=[
            SimpleNamespace(
                line_index=1,
                page_number=pagina_da_linha,
                located=True,
            ),
        ],
        barcodes=codigos,
    )


def test_controle_linha_valida_e_itf_identico_na_mesma_pagina():
    """Controle: mantém uma correspondência efetivamente verificável."""
    contexto = _contexto(
        codigos=[_codigo(conteudo=ITF_VIVO, pagina=1)],
    )
    [comparacao] = BarcodeNumericLineDetector().compare(contexto)
    assert comparacao.status == BarcodeLineComparisonStatus.MATCH
    assert comparacao.barcode_index == 1


def test_red_codigo_igual_em_outra_pagina_nao_confirma_correspondencia():
    """A coincidência numérica não basta quando as páginas divergem."""
    contexto = _contexto(
        codigos=[_codigo(conteudo=ITF_VIVO, pagina=2)],
        pagina_da_linha=1,
    )
    [comparacao] = BarcodeNumericLineDetector().compare(contexto)
    assert comparacao.status == BarcodeLineComparisonStatus.INCONCLUSIVE
    assert comparacao.barcode_index is None


def test_red_codigo_diferente_em_outra_pagina_nao_confirma_divergencia():
    """Uma cobrança de outra página não fundamenta um MISMATCH."""
    codigo_na_outra_pagina = "84680000006096900481000112943786092506903642"
    contexto = _contexto(
        codigos=[_codigo(conteudo=codigo_na_outra_pagina, pagina=2)],
        pagina_da_linha=1,
    )
    [comparacao] = BarcodeNumericLineDetector().compare(contexto)
    assert comparacao.status == BarcodeLineComparisonStatus.INCONCLUSIVE
    assert comparacao.barcode_index is None


def test_red_qrcode_numerico_nao_e_itf_de_pagamento():
    """Um QR Code com 44 algarismos não equivale a barras de pagamento."""
    contexto = _contexto(
        codigos=[
            _codigo(
                conteudo="1" * 44,
                pagina=1,
                formato="QRCode",
            ),
        ],
    )
    [comparacao] = BarcodeNumericLineDetector().compare(contexto)
    assert comparacao.status == BarcodeLineComparisonStatus.INCONCLUSIVE
    assert comparacao.barcode_index is None
