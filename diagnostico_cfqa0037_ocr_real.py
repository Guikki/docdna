"""Diagnóstico SOMENTE LEITURA da extração CF-QA 003.7, em um PDF real.

Na raiz do projeto, após copiar este arquivo:
  python diagnostico_cfqa0037_ocr_real.py --pdf "C:\\caminho\\fatura.pdf"
  python diagnostico_cfqa0037_ocr_real.py --sha <SHA-256 da aba 01 - Documentos>

O SHA procura dentro de settings.UPLOADS_DIR. Não reprocessa arquivos em lote,
não grava no storage, não altera análises já existentes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import re
from types import SimpleNamespace

from app.config.settings import settings
from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.readers.native_text_reader import NativeTextReader
from app.domain.readers.ocr_reader import OcrReader
from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.domain.services.financial_reconciliation_service import FinancialReconciliationService


def resolve_pdf(path_text: str | None, digest: str | None) -> Path:
    if path_text:
        path = Path(path_text).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != '.pdf':
            raise FileNotFoundError(f'PDF não encontrado: {path}')
        return path
    if not digest or not re.fullmatch(r'[0-9a-fA-F]{64}', digest):
        raise ValueError('Informe --pdf ou --sha com 64 caracteres hexadecimais')
    upload_dir = Path(settings.UPLOADS_DIR)
    if not upload_dir.is_dir():
        raise FileNotFoundError(f'UPLOADS_DIR não encontrado: {upload_dir}')
    for pdf in upload_dir.rglob('*.pdf'):
        h = sha256()
        with pdf.open('rb') as source:
            for chunk in iter(lambda: source.read(1048576), b''):
                h.update(chunk)
        if h.hexdigest().lower() == digest.lower():
            return pdf
    raise FileNotFoundError('Nenhum PDF com esse SHA-256 no storage/uploads')


def show_ocr_context(boxes: list) -> None:
    """Expõe linhas de OCR para diagnosticar textos perdidos pelo parser."""
    groups: dict[tuple[int,int], list] = {}
    for b in boxes:
        page = getattr(b, 'page_number', None)
        y = getattr(b, 'top', None)
        if not isinstance(page, int) or not isinstance(y, (int,float)):
            continue
        key = page, round(float(y)/12)
        groups.setdefault(key, []).append(b)
    print('\n--- LINHAS OCR QUE MENCIONAM RÓTULOS ---')
    count = 0
    for (page,_), words in sorted(groups.items()):
        text = ' '.join(str(w.text) for w in sorted(words, key=lambda w:w.left))
        if re.search(r'total|pagar|valor|conta|cliente|fatura|d.bito|titular', text, re.I):
            print(f'Página {page}: {text[:260]}')
            count += 1
            if count >= 35:
                print('[... limitado a 35 linhas]')
                break
    if not count:
        print('Nenhum rótulo reconhecível nas caixas OCR. Investigar OCR/resolução.')


def main() -> None:
    parser = argparse.ArgumentParser(description='CF-QA 003.7 | leitura real local, sem alterações')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--pdf', help='Caminho do PDF original')
    source.add_argument('--sha', help='SHA-256 informado na aba 01 - Documentos')
    args = parser.parse_args()
    pdf = resolve_pdf(args.pdf, args.sha)
    print('=' * 72)
    print('DOCDNA - CF-QA 003.7 | DIAGNÓSTICO REAL (SOMENTE LEITURA)')
    print('Arquivo:', pdf)
    ocr_result = OcrReader().read(str(pdf))
    native = NativeTextReader().read(str(pdf))
    bars = BarcodeReader().read(str(pdf))
    boxes = list(ocr_result.text_boxes)
    print(f'Caixas OCR: {len(boxes)} | Códigos decodificados: {len(bars)}')
    finance = FinancialReconciliationService().reconcile(
        barcodes=bars, native_text=native, ocr=ocr_result.document_ocr,
        ocr_text_boxes=boxes,
    )
    print('\n--- VALORES FINANCEIROS OBSERVADOS ---')
    for value in finance.values:
        print(f'{value.source}: R$ {value.amount:.2f} | página={value.page_number} '
              f'| origem={value.provenance} | confiança={value.confidence}')
    print('Status:', finance.status.value)
    print('Mensagem:', finance.message)
    identifiers = DocumentIdentifierService().extract(
        ocr_text_boxes=boxes, native_text=native, ocr=ocr_result.document_ocr,
    )
    print('\n--- IDENTIFICADORES OBSERVADOS ---')
    for item in identifiers:
        print(f'{item["label"]}: {item["value"]} | página={item.get("page_number")} '
              f'| origem={item.get("source")} | confiança={item.get("confidence")}')
    show_ocr_context(boxes)
    print('\nA ausência de um valor indica que ele NÃO foi confirmado pelo pipeline.')
    print('Este diagnóstico não conclui fraude, autenticidade ou mesma obrigação.')


if __name__ == '__main__':
    main()
