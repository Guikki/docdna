"""CF-QA 003.8: regressões com layout geométrico derivado de diagnóstico real.

Os valores deste teste são sintéticos. Coordenadas aproximam o relatório espacial
sem transformar os números dos documentos analisados em regras de produção.
"""
from decimal import Decimal
from types import SimpleNamespace as NS

from app.domain.services.financial_reconciliation_service import (
    FinancialReconciliationService, FinancialReconciliationStatus,
)
from app.domain.services.document_identifier_service import DocumentIdentifierService


def b(text, x, y, w, h=12, page=1, conf=95):
    return NS(text=text, left=x, top=y, width=w, height=h,
              page_number=page, confidence=conf)


def finance(boxes, barcodes=()):
    return FinancialReconciliationService().reconcile(
        barcodes=barcodes, native_text=NS(content=""), ocr=NS(content=""),
        ocr_text_boxes=boxes,
    )


def identifiers(boxes):
    return DocumentIdentifierService().extract(ocr_text_boxes=boxes)


def header_and_amount():
    """Duas colunas: vencimento e 'Valor a pagar' com valor na linha abaixo."""
    return [
        b("VENCIMENTO", 740, 355, 79, 11, conf=82),
        b("VALOR", 894, 355, 39, 11, conf=96),
        b("A", 937, 355, 8, 11, conf=96),
        b("PAGAR", 949, 355, 41, 11, conf=96),
        b("(R$)", 995, 355, 21, 14, conf=84),
        b("27/08/2026", 725, 369, 108, 17, conf=96),
        b("247,58", 921, 371, 65, 20, conf=96),
    ]


def receipt_rows():
    """Canhoto: duas etiquetas legíveis, terceira coluna sem rótulo claro."""
    return [
        b("Nida", 366, 1448, 25, 9, conf=67),
        b("Conta", 395, 1447, 27, 10, conf=93),
        b("Nida", 526, 1448, 25, 9, conf=75),
        b("Fatura", 555, 1448, 29, 9, conf=42),
        b("Mês", 665, 1448, 18, 9, conf=92),
        b("Referência", 688, 1448, 49, 9, conf=76),
        b("12345678901-2", 166, 1469, 114, conf=92),
        b("00000012345678", 332, 1469, 127, conf=92),
        b("00000012345679", 494, 1469, 128, conf=89),
        b("07/2026", 674, 1469, 58, conf=96),
    ]


def test_valor_impresso_abaixo_do_cabecalho_na_coluna_correta():
    result = finance(header_and_amount())
    found = [v for v in result.values if v.source == "PRINTED"]
    assert len(found) == 1
    assert found[0].amount == Decimal("247.58")
    assert found[0].page_number == 1
    assert found[0].left == 894
    assert found[0].confidence == 96
    assert found[0].provenance == "OCR_TEXT_BOX_PAIR"
    assert "27/08/2026" not in found[0].raw_content


def test_subtotais_nao_viram_total_impresso():
    boxes = header_and_amount() + [
        b("Subtotal", 114, 764, 41, 10),
        b("247,58", 614, 764, 37, 11),
        b("Subtotal", 114, 789, 41, 10),
        b("247,58", 614, 789, 37, 11),
    ]
    found = [v for v in finance(boxes).values if v.source == "PRINTED"]
    assert len(found) == 1
    assert found[0].top == 355


def test_valores_em_colunas_diferentes_nao_se_misturam():
    boxes = header_and_amount()
    boxes[-1] = b("247,58", 725, 371, 65, 20)
    assert [v for v in finance(boxes).values if v.source == "PRINTED"] == []


def test_valores_concorrentes_mesma_coluna_sao_ambiguos():
    boxes = header_and_amount() + [b("567,89", 931, 378, 52, 12)]
    assert [v for v in finance(boxes).values if v.source == "PRINTED"] == []


def test_nao_une_numero_de_conta_e_fatura_apesar_do_gap_estreito():
    data = {v["kind"]: v for v in identifiers(receipt_rows())}
    assert data["account"]["value"] == "00000012345678"
    assert data["invoice"]["value"] == "00000012345679"
    assert data["invoice"]["page_number"] == 1
    assert data["invoice"]["source"] == "OCR_BOX"
    assert data["invoice"]["confidence"] == 42.0
    assert "automatic_debit" not in data


def test_debito_sem_rotulo_nao_pode_ser_inferido_pela_coluna():
    data = identifiers(receipt_rows())
    assert all(obs["kind"] != "automatic_debit" for obs in data)


def test_debito_com_rotulo_proximo_e_confirmado():
    boxes = [b("Cód.", 166, 1448, 28, 9),
             b("Débito", 198, 1448, 42, 9),
             b("Automático", 243, 1448, 70, 9)]
    # A geometria muda para preservar alinhamento entre coluna e dado.
    boxes += [b("12345678901-2", 169, 1469, 137, 12)]
    observed = {v["kind"]: v for v in identifiers(boxes)}
    assert observed["automatic_debit"]["value"] == "123456789012"


def test_fatura_nao_recebe_identificador_de_outra_pagina():
    data = receipt_rows()
    data = [v if v.text != "00000012345679" else
            b("00000012345679", 494, 1469, 128, page=2, conf=89)
            for v in data]
    assert not any(v["kind"] == "invoice" for v in identifiers(data))


def test_comparador_enxerga_fatura_repetida_depois_da_extracao():
    a = identifiers(receipt_rows())
    x = identifiers(receipt_rows())
    result = DocumentIdentifierService().compare([
        {"id": "A", "original_filename": "a.pdf", "document_identifiers": a},
        {"id": "B", "original_filename": "b.pdf", "document_identifiers": x},
    ])
    assert any(v["kind"] == "invoice" and v["relation"] == "EXACT"
               for v in result)


def test_same_page_financial_comparison_does_not_claim_fraud():
    # Testar o elo com ITF e QR Code sem depender de imagem ou valores de caso real.
    svc = FinancialReconciliationService
    body = f"846{56123:011d}1234{'1' * 25}"
    itf = body[:3] + str(svc._modulo_10(body)) + body[3:]
    def tlv(t,v): return f"{t}{len(v.encode('utf-8')):02d}{v}"
    pix = (tlv('00','01') + tlv('26',tlv('00','br.gov.bcb.pix')+tlv('01','teste'))
           + tlv('53','986') + tlv('54','1.20') + tlv('58','BR')
           + tlv('59','TESTE') + tlv('60','SALVADOR') + '6304')
    pix += f"{svc._crc16_ccitt(pix.encode('utf-8')):04X}"
    codes = [NS(content=itf, format='ITF', barcode_index=1, page_number=1),
             NS(content=pix, format='QR Code', barcode_index=2, page_number=1)]
    result = finance(header_and_amount(), codes)
    assert result.status == FinancialReconciliationStatus.REVIEW_REQUIRED
    assert any(set(c.sources) == {'ITF','PIX','PRINTED'} and
               c.linkage == 'SAME_PAGE_UNCONFIRMED' for c in result.comparisons)
