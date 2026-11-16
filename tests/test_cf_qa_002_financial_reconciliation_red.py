"""CF-QA 002.2 — testes RED generalizados de reconciliação financeira.

OBJETIVO
--------
Definir o comportamento desejado para documentos DESCONHECIDOS, sem regras
baseadas em operadora, titular, número de processo, lote ou valor fixo.

Contrato proposto (ainda NÃO implementado em produção)::

    FinancialReconciliationService().reconcile(
        barcodes=list[Barcode],
        native_text=DocumentText(...),
        ocr=DocumentOcr(...),
    )

Retorno: `values` (cada item tem `source`, `amount`, `page_number` e
`barcode_index`, quando aplicáveis) e `status`. São aceitos dicts ou objetos.

Os estados usados nos testes são:
- REVIEW_REQUIRED: diferenças que justificam TRIAGEM, não prova de fraude;
- INCONCLUSIVE: dados insuficientes / associação incerta;
- outros estados podem existir, desde que não contradigam estas regras.

IMPORTANTE
----------
- O texto de DocumentText e DocumentOcr é agregado; ele NÃO informa em qual
  página cada valor foi impresso. Não atribuir página por suposição.
- A associação inequívoca entre valores deve ser tratada posteriormente com
  evidências localizadas (spans OCR/nativos e seções de cobrança).
- O código de produção ainda não existe; ModuleNotFoundError nos testes RED
  NÃO equivale a demonstração de falhas de algoritmos individuais.
- Os construtores de ITF e Pix neste arquivo criam EXEMPLOS SINTÉTICOS válidos.
"""

from __future__ import annotations

from decimal import Decimal
from importlib import import_module
from random import Random

import pytest

from app.domain.models.barcode import Barcode
from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.document_text import DocumentText
from app.domain.models.numeric_line_validation import NumericLineValidationStatus
from app.domain.rules.numeric_line_validator import NumericLineValidator


def _dv_modulo_10(digits: str) -> int:
    """Cálculo independente para gerar casos de arrecadação sintéticos."""
    total = 0
    peso = 2
    for character in reversed(digits):
        produto = int(character) * peso
        total += produto // 10 + produto % 10
        peso = 1 if peso == 2 else 2
    return (10 - total % 10) % 10


def _dv_modulo_11_arrecadacao(digits: str) -> int:
    """Módulo 11 de arrecadação; não é o DV geral do boleto bancário."""
    total = 0
    peso = 2
    for character in reversed(digits):
        total += int(character) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = total % 11
    if resto in (0, 1):
        return 0
    if resto == 10:
        return 1
    return 11 - resto


def _arrecadacao(
    centavos: int,
    *,
    segmento: int = 2,
    indicador: int = 6,
    campo_livre: str = "1234567890123456789012345",
    conveniada: str = "1357",
) -> str:
    """Gera código de 44 dígitos com DV geral calculado, sem marca específica.

    Indicadores 6/8 contêm valor efetivo; 7/9 contêm quantidade/referência.
    """
    assert 0 <= centavos <= 99_999_999_999
    assert segmento in (1, 2, 3, 4, 5, 6, 7, 9)
    assert indicador in (6, 7, 8, 9)
    assert len(campo_livre) == 25 and campo_livre.isdigit()
    assert len(conveniada) == 4 and conveniada.isdigit()
    dados = f"8{segmento}{indicador}{centavos:011d}{conveniada}{campo_livre}"
    assert len(dados) == 43
    calculadora = (
        _dv_modulo_10 if indicador in (6, 7) else _dv_modulo_11_arrecadacao
    )
    codigo = dados[:3] + str(calculadora(dados)) + dados[3:]
    assert len(codigo) == 44
    return codigo


def _campo(tag: str, value: str) -> str:
    assert len(tag) == 2 and len(value.encode("utf-8")) < 100
    # Os casos sintéticos usam caracteres ASCII dentro dos campos.
    assert value.isascii()
    return f"{tag}{len(value):02d}{value}"


def _crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _pix(
    valor: str | None = "25.31",
    *,
    dinamico: bool = False,
    moeda: str = "986",
    txid: str = "DOC123",
) -> str:
    """Gera BR Code sintético com estrutura TLV e CRC válido."""
    dados_recebedor = _campo("00", "br.gov.bcb.pix")
    if dinamico:
        dados_recebedor += _campo("25", "pay.example.org/cobranca/123")
    else:
        dados_recebedor += _campo("01", "123e4567-e12b-12d1-a456-426655440000")
    fields = [
        _campo("00", "01"),
        _campo("01", "12" if dinamico else "11"),
        _campo("26", dados_recebedor),
        _campo("52", "0000"),
        _campo("53", moeda),
    ]
    if valor is not None:
        fields.append(_campo("54", valor))
    fields += [
        _campo("58", "BR"),
        _campo("59", "RECEBEDOR TESTE"),
        _campo("60", "CIDADE TESTE"),
        _campo("62", _campo("05", txid)),
    ]
    payload_without_crc = "".join(fields) + "6304"
    return payload_without_crc + _crc16_ccitt(payload_without_crc)


def _barcode(
    content: str,
    *,
    formato: str = "ITF",
    pagina: int = 1,
    indice: int = 1,
) -> Barcode:
    return Barcode(
        barcode_index=indice,
        page_number=pagina,
        format=formato,
        content=content,
    )


def _texto(content: str, *, paginas: int = 1) -> DocumentText:
    return DocumentText(
        content=content,
        character_count=len(content),
        pages_with_text=paginas if content else 0,
    )


def _ocr(content: str) -> DocumentOcr:
    return DocumentOcr(
        content=content,
        character_count=len(content),
        pages_processed=1,
        pages_with_text=1 if content else 0,
        language="por",
    )


def _field(obj, key: str):
    return obj[key] if isinstance(obj, dict) else getattr(obj, key)


def _result(*, barcodes=(), texto: str = "", ocr: str = "", paginas_texto: int = 1):
    # Importar somente quando o teste roda. Assim, testes-controle continuam
    # executáveis durante a fase RED, antes de existir o serviço.
    module = import_module("app.domain.services.financial_reconciliation_service")
    return module.FinancialReconciliationService().reconcile(
        barcodes=list(barcodes),
        native_text=_texto(texto, paginas=paginas_texto),
        ocr=_ocr(ocr),
    )


def _values(result, source: str):
    return [
        value
        for value in _field(result, "values")
        if str(_field(value, "source")).upper() == source.upper()
    ]


def _status(result) -> str:
    status = _field(result, "status")
    return str(getattr(status, "value", status)).upper()


def _amounts(result, source: str) -> list[Decimal]:
    return [_field(item, "amount") for item in _values(result, source)]


# -------------------------------------------------------------------------
# Controles puros: não dependem do novo serviço.
# -------------------------------------------------------------------------


def test_controle_codigo_arrecadacao_tem_44_digitos_e_dv_consistente():
    for indicador in (6, 7, 8, 9):
        codigo = _arrecadacao(12_345, indicador=indicador)
        assert len(codigo) == 44
        dados = codigo[:3] + codigo[4:]
        modulo = _dv_modulo_10 if indicador in (6, 7) else _dv_modulo_11_arrecadacao
        assert codigo[3] == str(modulo(dados))


def test_controle_linha_arrecadacao_de_48_digitos_continua_valida():
    codigo = _arrecadacao(16_725, indicador=6)
    blocos = [codigo[i : i + 11] for i in range(0, 44, 11)]
    linha = "".join(bloco + str(_dv_modulo_10(bloco)) for bloco in blocos)
    validacao = NumericLineValidator().validate(
        type("Linha", (), {"line_index": 1, "normalized_content": linha})()
    )
    assert validacao.status == NumericLineValidationStatus.VALID


def test_controle_pix_sintetico_crc_confere_em_valores_variados():
    for valor in ("0.01", "37.49", "1250.75"):
        payload = _pix(valor)
        assert payload[-4:] == _crc16_ccitt(payload[:-4])


# -------------------------------------------------------------------------
# RED 1 — interpretação de valores conforme a norma e a origem.
# -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("segmento", "centavos", "pagina", "indice"),
    [
        (2, 1, 1, 2),        # Saneamento e valor mínimo
        (3, 8_765, 3, 5),    # Energia elétrica e gás
        (4, 128_999, 1, 7),  # Telecomunicações
        (5, 10_450_125, 2, 9),  # Órgãos governamentais
    ],
)
def test_red_itf_valor_efetivo_generico_e_origem(
    segmento: int, centavos: int, pagina: int, indice: int,
):
    codigo = _arrecadacao(centavos, segmento=segmento)
    result = _result(barcodes=[_barcode(codigo, pagina=pagina, indice=indice)])
    [value] = _values(result, "ITF")
    assert _field(value, "amount") == Decimal(centavos) / 100
    assert _field(value, "page_number") == pagina
    assert _field(value, "barcode_index") == indice


def test_red_arrecadacao_modulo11_indicador_8_valor_efetivo():
    cents = 738_920
    result = _result(barcodes=[_barcode(_arrecadacao(cents, indicador=8))])
    assert _amounts(result, "ITF") == [Decimal(cents) / 100]


@pytest.mark.parametrize("indicador", [7, 9])
def test_red_quantidade_de_moeda_nao_pode_virar_reais(indicador: int):
    codigo = _arrecadacao(52_600, indicador=indicador)
    result = _result(barcodes=[_barcode(codigo)])
    assert _values(result, "ITF") == []
    assert _status(result) == "INCONCLUSIVE"


def test_red_dv_geral_invalido_nao_produz_valor_confiavel():
    codigo = _arrecadacao(84_305)
    dv_alterado = str((int(codigo[3]) + 1) % 10)
    alterado = codigo[:3] + dv_alterado + codigo[4:]
    result = _result(barcodes=[_barcode(alterado)])
    assert _values(result, "ITF") == []


def test_red_qrcode_numerico_nao_e_codigo_itf():
    codigo = _arrecadacao(72_531)
    result = _result(barcodes=[_barcode(codigo, formato="QRCode")])
    assert _values(result, "ITF") == []


def test_red_codigo_bancario_nao_e_tratado_como_arrecadacao():
    codigo_bancario = "0019" + "0" * 40
    result = _result(barcodes=[_barcode(codigo_bancario)])
    assert _values(result, "ITF") == []


# -------------------------------------------------------------------------
# RED 2 — BR Code: CRC, campo de valor e ausência de dados confiáveis.
# -------------------------------------------------------------------------


@pytest.mark.parametrize("valor", ["0.01", "37.49", "1250.75"])
def test_red_pix_valor_tlv_valido_sem_dependencia_de_exemplo(valor: str):
    result = _result(barcodes=[_barcode(_pix(valor), formato="QRCode", indice=6)])
    [payment_value] = _values(result, "PIX")
    assert _field(payment_value, "amount") == Decimal(valor)
    assert _field(payment_value, "barcode_index") == 6
    assert _field(payment_value, "page_number") == 1


def test_red_pix_crc_errado_nao_e_interpretado_como_valor_valido():
    payload = _pix("91.21")
    corrompido = payload[:-1] + ("0" if payload[-1] != "0" else "1")
    result = _result(barcodes=[_barcode(corrompido, formato="QRCode")])
    assert _values(result, "PIX") == []


@pytest.mark.parametrize("dinamico", [False, True])
def test_red_pix_sem_campo_54_nao_inventa_valor(dinamico: bool):
    result = _result(barcodes=[_barcode(_pix(None, dinamico=dinamico), formato="QRCode")])
    assert _values(result, "PIX") == []
    assert _status(result) == "INCONCLUSIVE"


def test_red_moeda_pix_diferente_de_brl_nao_e_rotulada_como_reais():
    result = _result(barcodes=[_barcode(_pix("35.90", moeda="840"), formato="QRCode")])
    assert _values(result, "PIX") == []


def test_red_qrcode_nao_pix_nao_deve_gerar_valor_pix():
    result = _result(barcodes=[_barcode("https://example.org/arquivo?id=54", formato="QRCode")])
    assert _values(result, "PIX") == []


# -------------------------------------------------------------------------
# RED 3 — contexto semântico: valor devido != desconto != outros preços.
# -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Conta de consumo. Total a pagar: R$ 1.234,56.", Decimal("1234.56")),
        ("Imposto. Valor a pagar R$ 89,10.", Decimal("89.10")),
        ("Serviços. Total devido: R$ 215,00.", Decimal("215.00")),
    ],
)
def test_red_lexico_generico_valor_total_contextualizado(texto: str, esperado: Decimal):
    result = _result(texto=texto)
    assert esperado in _amounts(result, "PRINTED")


def test_red_desconto_e_preco_unitario_nao_sao_total_a_pagar():
    result = _result(texto=(
        "Preço do plano: R$ 80,00. Desconto: R$ 15,00. "
        "Valor a pagar: R$ 65,00."
    ))
    assert _amounts(result, "PRINTED") == [Decimal("65.00")]


def test_red_valor_solto_sem_papel_de_cobranca_nao_vira_total_impresso():
    result = _result(texto="Protocolo 12345678. Exemplo de R$ 87,45.")
    assert _values(result, "PRINTED") == []


def test_red_ocr_de_numero_ambiguo_nao_produz_valor_confiavel():
    result = _result(ocr="Total a pagar: R$ 1O9,90")  # letra O, não zero
    assert _values(result, "PRINTED") == []


def test_red_sequencia_binaria_nao_e_dado_financeiro():
    bits = "01" * 25
    result = _result(texto=f"Dados técnicos {bits}", ocr=bits)
    assert _field(result, "values") == []
    assert _status(result) == "INCONCLUSIVE"


# -------------------------------------------------------------------------
# RED 4 — correlação conservadora, precisão e independência do lote.
# -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("centavos_itf", "valor_pix"),
    [(2_500, "25.00"), (89_990, "899.90"), (103_501, "1035.01")],
)
def test_red_valores_equivalentes_nao_geram_revisao_falsa(
    centavos_itf: int, valor_pix: str,
):
    result = _result(barcodes=[
        _barcode(_arrecadacao(centavos_itf), indice=1),
        _barcode(_pix(valor_pix), formato="QRCode", indice=2),
    ])
    assert _status(result) != "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("centavos_itf", "valor_pix"),
    [(2_500, "20.00"), (89_990, "1.00"), (103_501, "900.00")],
)
def test_red_itf_e_pix_distintos_na_mesma_pagina_exigem_triagem_nao_fraude(
    centavos_itf: int, valor_pix: str,
):
    result = _result(barcodes=[
        _barcode(_arrecadacao(centavos_itf), indice=1),
        _barcode(_pix(valor_pix), formato="QRCode", indice=2),
    ])
    assert _status(result) == "REVIEW_REQUIRED"
    assert "FRAUD" not in _status(result)


def test_red_duas_cobrancas_distintas_na_mesma_pagina_sao_ambiguas():
    # Mesmo documento com múltiplas cobranças: não se deve comparar
    # indiscriminadamente o primeiro ITF com o primeiro Pix.
    result = _result(barcodes=[
        _barcode(_arrecadacao(10_000, campo_livre="1" * 25), indice=1),
        _barcode(_arrecadacao(20_000, campo_livre="2" * 25), indice=2),
        _barcode(_pix("100.00", txid="PAGAMENTO1"), formato="QRCode", indice=3),
        _barcode(_pix("200.00", txid="PAGAMENTO2"), formato="QRCode", indice=4),
    ])
    assert _status(result) != "REVIEW_REQUIRED"


def test_red_itf_e_pix_em_paginas_distintas_nao_provam_uma_cobranca():
    result = _result(barcodes=[
        _barcode(_arrecadacao(15_000), pagina=1, indice=1),
        _barcode(_pix("100.00"), formato="QRCode", pagina=2, indice=2),
    ])
    assert _status(result) == "INCONCLUSIVE"


def test_red_texto_agregado_de_varias_paginas_nao_recebe_localizacao_inventada():
    result = _result(
        barcodes=[_barcode(_arrecadacao(12_300), pagina=2)],
        texto="Valor a pagar: R$ 123,00",
        paginas_texto=2,
    )
    for value in _values(result, "PRINTED"):
        assert _field(value, "page_number") is None


def test_red_duas_fontes_de_texto_com_mesmo_valor_nao_geram_divergencia():
    result = _result(
        texto="Valor a pagar: R$ 87,65",
        ocr="Valor a pagar: R$ 87,65",
    )
    assert _status(result) != "REVIEW_REQUIRED"


def test_red_a_ordem_das_barras_nao_pode_mudar_o_resultado():
    barcodes = [
        _barcode(_arrecadacao(4_100), indice=1),
        _barcode(_pix("41.00"), formato="QRCode", indice=2),
    ]
    forward = _result(barcodes=barcodes)
    reversed_result = _result(barcodes=list(reversed(barcodes)))
    assert _status(forward) == _status(reversed_result)
    assert sorted(_amounts(forward, "ITF")) == sorted(_amounts(reversed_result, "ITF"))
    assert sorted(_amounts(forward, "PIX")) == sorted(_amounts(reversed_result, "PIX"))


def test_red_analises_separadas_nao_compartilham_valores_anteriores():
    primeiro = _result(barcodes=[_barcode(_arrecadacao(76_550))])
    segundo = _result(barcodes=[_barcode(_arrecadacao(32_100))])
    assert _amounts(primeiro, "ITF") == [Decimal("765.50")]
    assert _amounts(segundo, "ITF") == [Decimal("321.00")]


def test_red_diversos_valores_gerados_sem_numeros_de_caso_real():
    # Validação determinística de múltiplos valores e segmentos: não depende
    # de dados das faturas que motivaram a auditoria.
    gerador = Random(20261021)
    for indice in range(24):
        centavos = gerador.randint(1, 50_000_000)
        segmento = gerador.choice((2, 3, 4, 5, 6))
        result = _result(barcodes=[
            _barcode(
                _arrecadacao(centavos, segmento=segmento, conveniada=f"{1000 + indice:04d}"),
                indice=indice + 1,
            )
        ])
        assert _amounts(result, "ITF") == [Decimal(centavos) / 100]
