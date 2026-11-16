"""Cenários de segurança complementares para a correção do comparador."""
from types import SimpleNamespace
from app.domain.detectors.barcode_numeric_line_detector import BarcodeNumericLineDetector
from app.domain.models.barcode_line_comparison import BarcodeLineComparisonStatus as Status
from app.domain.models.numeric_line_validation import NumericLineValidationStatus
from app.domain.rules.numeric_line_converter import NumericLineConverter
from app.domain.rules.numeric_line_validator import NumericLineValidator

ITF_VIVO = "84680000006096900481000112943786092506903643"
LINHA_VIVO_CORRESPONDENTE = "846800000065096900481001011294378606925069036430"

def _linha_validada():
    linha = SimpleNamespace(line_index=1, normalized_content=LINHA_VIVO_CORRESPONDENTE)
    validacao = NumericLineValidator().validate(linha)
    assert validacao.status == NumericLineValidationStatus.VALID
    assert NumericLineConverter().convert_to_barcode(validacao) == ITF_VIVO
    return validacao

def _codigo(*, conteudo, pagina, formato="ITF"):
    return SimpleNamespace(barcode_index=1, page_number=pagina, format=formato, content=conteudo)

def _ctx(codigos, locais=None, validations=None):
    return SimpleNamespace(
        numeric_line_validations=validations if validations is not None else [_linha_validada()],
        numeric_line_locations=locais or [],
        barcodes=codigos,
    )

def _loc(pagina=1):
    return SimpleNamespace(line_index=1, page_number=pagina, located=True)

def test_sem_localizacao_nao_fabrica_correspondencia():
    [c] = BarcodeNumericLineDetector().compare(_ctx([_codigo(conteudo=ITF_VIVO,pagina=1)]))
    assert c.status is Status.INCONCLUSIVE
    assert c.barcode_index is None

def test_multiplos_itfs_diferentes_na_pagina_nao_fabricam_pareamento():
    codigos=[_codigo(conteudo=ITF_VIVO, pagina=1),
             SimpleNamespace(barcode_index=2,page_number=1, format="ITF", content=ITF_VIVO[:-1]+"2")]
    [c] = BarcodeNumericLineDetector().compare(_ctx(codigos, [_loc(1)]))
    assert c.status is Status.INCONCLUSIVE

def test_varias_copias_do_mesmo_itf_na_pagina_permitem_comparar_conteudo():
    codigos=[_codigo(conteudo=ITF_VIVO,pagina=1),
             SimpleNamespace(barcode_index=2,page_number=1,format="ITF",content=ITF_VIVO)]
    [c] = BarcodeNumericLineDetector().compare(_ctx(codigos, [_loc(1)]))
    assert c.status is Status.MATCH

def test_mesma_pagina_uma_linha_valida_um_itf_diferente_e_mismatch():
    [c] = BarcodeNumericLineDetector().compare(_ctx(
        [_codigo(conteudo=ITF_VIVO[:-1]+"2",pagina=1)], [_loc(1)]))
    assert c.status is Status.MISMATCH

def test_qr_numerico_identico_a_linha_nao_confirmara_match():
    [c] = BarcodeNumericLineDetector().compare(_ctx(
        [_codigo(conteudo=ITF_VIVO,pagina=1,formato="QRCode")], [_loc(1)]))
    assert c.status is Status.INCONCLUSIVE

def test_localizacoes_conflitantes_nao_escolhem_pagina():
    [c] = BarcodeNumericLineDetector().compare(_ctx(
        [_codigo(conteudo=ITF_VIVO,pagina=1)], [_loc(1),_loc(2)]))
    assert c.status is Status.INCONCLUSIVE

def test_sem_codigos_itf_na_mesma_pagina_e_inconclusive():
    [c] = BarcodeNumericLineDetector().compare(_ctx(
        [_codigo(conteudo=ITF_VIVO,pagina=2)], [_loc(1)]))
    assert c.status is Status.INCONCLUSIVE

def test_codigo_de_44_digitos_de_outro_formato_nao_fundamenta_mismatch():
    [c] = BarcodeNumericLineDetector().compare(_ctx(
        [_codigo(conteudo="2"*44,pagina=1, formato="Code128")], [_loc(1)]))
    assert c.status is Status.INCONCLUSIVE
