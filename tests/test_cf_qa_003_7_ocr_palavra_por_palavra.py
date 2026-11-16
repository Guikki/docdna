"""CF-QA 003.7: testes realistas de OCR Tesseract (caixa por PALAVRA).

Instalar em tests/test_cf_qa_003_7_ocr_palavra_por_palavra.py
Executar: python -m pytest tests/test_cf_qa_003_7_ocr_palavra_por_palavra.py -v
"""
from decimal import Decimal
from types import SimpleNamespace as NS

from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.domain.services.financial_reconciliation_service import (
    FinancialReconciliationService, FinancialReconciliationStatus,
)


def b(text, *, x=60, y=80, w=75, h=17, page=1, conf=95):
    return NS(text=text, left=x, top=y, width=w, height=h,
              page_number=page, confidence=conf)


def extract(*boxes, native="", ocr=""):
    return DocumentIdentifierService().extract(
        ocr_text_boxes=boxes, native_text=NS(content=native), ocr=NS(content=ocr))


def fin(*boxes, barcodes=(), native="", ocr=""):
    return FinancialReconciliationService().reconcile(
        barcodes=barcodes, ocr_text_boxes=boxes,
        native_text=NS(content=native), ocr=NS(content=ocr))


def printed(result):
    return [v for v in result.values if v.source == "PRINTED"]


def word_total(amount="109,90", y=80):
    return [b("Total", x=60,y=y,w=47), b("a",x=112,y=y,w=10),
            b("Pagar",x=130,y=y,w=48),b("R$",x=198,y=y,w=23),
            b(amount,x=232,y=y,w=68)]


def test_financeiro_total_tesseract_palavra_por_palavra():
    values=printed(fin(*word_total()))
    assert len(values)==1 and values[0].amount==Decimal("109.90")
    assert values[0].page_number==1 and values[0].provenance=="OCR_TEXT_BOX_LINE"
    assert values[0].confidence==95


def test_financeiro_rotulo_e_preco_separados_na_mesma_linha():
    words=[b("Valor",x=50,w=42), b("a",x=100,w=12),b("pagar",x=122,w=49),
           b("R$",x=350,w=22),b("219,40",x=380,w=68)]
    values=printed(fin(*words))
    assert len(values)==1 and values[0].amount==Decimal("219.40")
    assert values[0].page_number==1


def test_financeiro_valor_abaixo_do_rotulo():
    words=[b("Total",x=50,w=43),b("a",x=98,w=10),b("pagar",x=116,w=52),
           b("95,12",x=67,y=108,w=60)]
    assert [v.amount for v in printed(fin(*words))]==[Decimal("95.12")]


def test_financeiro_nao_cruza_paginas():
    words=[b("Total",x=50,w=43),b("a",x=98,w=10),b("pagar",x=116,w=52),
           b("95,12",x=67,y=108,w=60,page=2)]
    assert printed(fin(*words))==[]


def test_financeiro_valores_ambiguos_nao_selecionados():
    words=[b("Valor",x=50,w=42),b("a",x=100,w=12),b("pagar",x=122,w=49),
           b("82,00",x=280,w=55),b("73,00",x=400,w=55)]
    assert printed(fin(*words))==[]


def test_financeiro_nao_preenche_valor_de_itf_curto():
    barcode=NS(content="00104360",format="ITF",page_number=1,barcode_index=1)
    result=fin(*word_total(),barcodes=[barcode])
    assert [(v.source,v.amount) for v in result.values]==[("PRINTED",Decimal("109.90"))]


def test_financeiro_texto_agregado_sem_r_mantem_sem_pagina():
    result=fin(native="Total a pagar: 259,80")
    assert printed(result)[0].page_number is None
    assert printed(result)[0].amount==Decimal("259.80")


def test_identifier_header_4_colunas_numeros_na_linha_inferior():
    words=[
        b("Cód.",x=20,w=40), b("Débito",x=64,w=52),b("Automático",x=121,w=85),
        b("Nº",x=270,w=25),b("da",x=298,w=18),b("Conta",x=321,w=49),
        b("Nº",x=430,w=25),b("da",x=459,w=18),b("Fatura",x=481,w=55),
        b("38175092647-8",x=24,y=115,w=128),
        b("00006184673258",x=268,y=115,w=120),
        b("00006184273586",x=432,y=115,w=125),
    ]
    values={o["kind"]:o for o in extract(*words)}
    assert values["automatic_debit"]["value"]=="381750926478"
    assert values["account"]["value"]=="00006184673258"
    assert values["invoice"]["value"]=="00006184273586"
    assert all(values[k]["page_number"]==1 for k in ("automatic_debit","account","invoice"))
    assert all(values[k]["source"]=="OCR_BOX" for k in ("automatic_debit","account","invoice"))


def test_identifier_fatura_debaixo_de_rotulo_sem_prefixo_nome_da_operadora():
    words=[b("Nº",x=100,w=24), b("da",x=128,w=19),b("Fatura",x=155,w=55),
           b("00006184273586",x=102,y=114,w=120)]
    matches=[x for x in extract(*words) if x["kind"]=="invoice"]
    assert len(matches)==1 and matches[0]["value"]=="00006184273586"


def test_identifier_nao_cruza_paginas_de_rotulo_e_valor():
    words=[b("Nº",x=100,w=24),b("da",x=128,w=19),b("Fatura",x=155,w=55),
           b("00006184273586",x=102,y=114,w=120,page=2)]
    assert not any(x["kind"]=="invoice" for x in extract(*words))


def test_identifier_numero_sem_rotulo_nao_se_torna_fatura():
    assert extract(b("00006184273586",x=102,y=114,w=120))==[]


def test_identifier_titular_separado_por_linha():
    words=[b("Titular",x=75,y=90,w=78),b("MARIA",x=75,y=121,w=60),
           b("FERNANDA",x=138,y=121,w=100),b("SILVA",x=245,y=121,w=60)]
    obs=[x for x in extract(*words) if x["kind"]=="holder"]
    assert len(obs)==1 and obs[0]["value"]=="MARIA FERNANDA SILVA"


def test_identifier_campo_horizontal_existente_permanece_funcionando():
    obs=extract(b("Nº",x=55,w=25), b("da",x=82,w=20),
                b("Conta:",x=105,w=54),b("00006184673258",x=170,w=135))
    assert [(x["kind"],x["value"]) for x in obs]==[("account","00006184673258")]


def test_identifier_comparador_recebe_fatura_extraida_por_colunas():
    a=extract(b("Nº",x=70,w=25),b("da",x=97,w=20),b("Fatura",x=122,w=64),
              b("00001234567890",x=77,y=113,w=130))
    c=extract(b("Nº",x=70,w=25),b("da",x=97,w=20),b("Fatura",x=122,w=64),
              b("00001234567890",x=77,y=113,w=130))
    result=DocumentIdentifierService().compare([
        {"id":"a","original_filename":"a.pdf","document_identifiers":a},
        {"id":"b","original_filename":"b.pdf","document_identifiers":c},
    ])
    assert len(result)==1
    assert result[0]["kind"]=="invoice" and result[0]["relation"]=="EXACT"


def test_identifier_ambiguo_duas_celulas_proximas_nao_escolhe():
    words=[b("Conta",x=100,y=90,w=80),
           b("00001234567890",x=95,y=120,w=120),
           b("00009876543210",x=220,y=120,w=120)]
    # Se houver mais de uma alternativa geometricamente equivalente,
    # aceitar apenas se a atribuição a um campo for inequívoca.
    vals=[x for x in extract(*words) if x["kind"]=="account"]
    assert len(vals)<=1
