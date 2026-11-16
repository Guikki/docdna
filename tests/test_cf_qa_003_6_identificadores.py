"""CF-QA 003.6 — testes de campos com rótulo e comparação conservadora.

Estes testes não dependem das faturas Vivo nem de nomes de pessoas reais.
Execute: python -m pytest tests/test_cf_qa_003_6_identificadores.py -v
"""
from __future__ import annotations
from types import SimpleNamespace as NS

from app.domain.services.document_identifier_service import DocumentIdentifierService


def box(text, *, page=1, x=100, y=100, w=180, h=20, conf=95):
    return NS(text=text, page_number=page, left=x, top=y, width=w, height=h, confidence=conf)


def doc(aid, name, fields):
    return {"id": aid, "original_filename": name, "document_identifiers": fields}


def extract(*boxes, native="", ocr=""):
    return DocumentIdentifierService().extract(
        ocr_text_boxes=boxes, native_text=NS(content=native), ocr=NS(content=ocr)
    )


def f(kind, value, source="OCR_BOX", confidence=99):
    return {"kind": kind, "value": value, "source": source,
            "page_number": 1 if source == "OCR_BOX" else None,
            "confidence": confidence, "raw_excerpt": f"{kind}: {value}"}


def test_ocr_localizado_preserva_zeros_pagina_e_confiança():
    [item] = extract(box("Nº conta: 00007812003456", page=3, conf=87))
    assert (item["kind"], item["value"], item["page_number"]) == ("account", "00007812003456", 3)
    assert (item["left"], item["top"], item["confidence"]) == (100, 100, 87)


def test_identifica_cada_campo_pelo_proprio_rotulo():
    items = extract(
        box("Conta: 00007812003456", y=100),
        box("Cliente: 00003456007812", y=140),
        box("Fatura: 00007812345600", y=180),
        box("Débito automático: 73284015629-0", y=220),
    )
    assert {i["kind"] for i in items} == {"account", "customer", "invoice", "automatic_debit"}
    assert next(i["value"] for i in items if i["kind"]=="automatic_debit") == "732840156290"


def test_rotulo_e_valor_em_caixas_distintas_mesma_linha():
    items = extract(box("Código do cliente:", x=100,w=190), box("00001357924680",x=310,w=165))
    assert len(items) == 1 and items[0]["kind"] == "customer"


def test_nao_une_colunas_distantes_mesmo_y():
    items = extract(box("Conta:", x=50, w=90), box("00001357924680", x=680, w=120))
    assert items == []


def test_nao_une_paginas_diferentes():
    items = extract(box("Conta:", page=1), box("00001357924680",page=2))
    assert items == []


def test_sem_rotulo_nao_inventa_tipo_cadastral():
    assert extract(box("00001357924680"), ocr="00001357924680") == []


def test_texto_agregado_nao_recebe_pagina_inventada():
    [item] = extract(native="Nº da fatura: 00001357924680")
    assert item["source"] == "NATIVE_AGGREGATED"
    assert item["page_number"] is None and item["left"] is None


def test_ocr_localizado_e_preferido_a_texto_agregado_igual():
    [item] = extract(box("Conta: 00001357924680", conf=42), ocr="Conta: 00001357924680")
    assert item["source"] == "OCR_BOX" and item["confidence"] == 42


def test_mesmo_numero_em_pagina_diferente_mantem_ocorrencia():
    items = extract(box("Conta: 00001357924680",page=1), box("Conta: 00001357924680",page=2))
    assert [i["page_number"] for i in items] == [1, 2]


def test_titular_explicito_extraido_sem_deduzir_identidade():
    [item] = extract(box("Titular: JULIANA FERNANDES COSTA"))
    assert (item["kind"],item["value"]) == ("holder","JULIANA FERNANDES COSTA")


def test_repeticao_exata_mesmo_tipo_e_titulares_distintos():
    shared = f("account","00007812003456")
    a = doc("a","um.pdf", [shared, f("holder","JULIANA FERNANDES COSTA")])
    b = doc("b","dois.pdf", [shared, f("holder","EDUARDO SOARES BARRETO")])
    [match] = DocumentIdentifierService().compare([a,b])
    assert match["code"] == "DOCUMENT_IDENTIFIER_EXACT_MATCH"
    assert match["kind"] == "account"
    assert match["document_count"] == 2
    assert match["severity"] == "Revisão recomendada"
    assert "não comprova adulteração" in match["description"]


def test_mesmo_numero_em_tipos_distintos_nao_compara():
    same="00007812003456"
    assert DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("account", same)]),
        doc("b","b.pdf",[f("invoice", same)]),
    ]) == []


def test_uma_pessoa_em_duas_faturas_nao_prova_fraude():
    common="00007812003456"
    matches = DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("account", common), f("holder","JOAO SILVA PEREIRA")]),
        doc("b","b.pdf",[f("account", common), f("holder","JOAO SILVA PEREIRA")]),
    ])
    assert matches[0]["severity"] == "Informativo"


def test_ocr_de_baixa_confianca_bloqueia_quase_igualdade():
    assert DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("invoice","00007812003456",confidence=30)]),
        doc("b","b.pdf",[f("invoice","00007812003457")]),
    ]) == []


def test_transposicao_adjacente_e_identificada_com_alta_confianca():
    results = DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("invoice","00007812003456")]),
        doc("b","b.pdf",[f("invoice","00007812003465")]),
    ])
    assert len(results) == 1 and results[0]["relation"] == "TRANSPOSITION"


def test_um_digito_diferente_e_identificado_sem_ser_prova():
    results = DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("invoice","00007812003456")]),
        doc("b","b.pdf",[f("invoice","00007812003457")]),
    ])
    assert len(results) == 1 and results[0]["relation"] == "ONE_DIGIT"
    assert results[0]["severity"] == "Informativo"


def test_dois_identificadores_conflitantes_no_mesmo_pdf_bloqueiam_comparacao():
    results = DocumentIdentifierService().compare([
        doc("a","a.pdf",[f("account","00007812003456"),f("account","00007812003457")]),
        doc("b","b.pdf",[f("account","00007812003456")]),
    ])
    assert results == []


def test_um_documento_so_nao_produz_comparacao():
    assert DocumentIdentifierService().compare([doc("a","a.pdf",[f("account","00007812003456")])]) == []


def test_sem_document_identifiers_nao_inventa_achados_anteriores():
    assert DocumentIdentifierService().compare([{"id":"a", "original_filename":"antigo.pdf"},
        {"id":"b", "original_filename":"outro.pdf"}]) == []


def test_500_documentos_sem_duplicacao_nao_explodem_comparador():
    docs = [doc(str(i),f"{i}.pdf", [f("account",f"{i:014d}")]) for i in range(500)]
    matches = DocumentIdentifierService().compare(docs)
    assert isinstance(matches,list)
    assert len(matches) <= DocumentIdentifierService._MAX_MATCHES
