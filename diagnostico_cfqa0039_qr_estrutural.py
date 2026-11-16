"""CF-QA 003.9.1: diagnóstico somente leitura de fontes QR/bits nativos.

Na raiz do DocDNA:
    python diagnostico_cfqa0039_qr_estrutural.py --sha SHA256
    python diagnostico_cfqa0039_qr_estrutural.py --pdf caminho.pdf
    python diagnostico_cfqa0039_qr_estrutural.py --sha SHA256 --with-barcodes

Sem --with-barcodes não executa o ZXing; somente examina estrutura nativa.
Não interpreta um indício de fonte QR como prova de QR oculto.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from app.domain.services.qr_structural_inspector import QrStructuralInspector
from app.domain.services.encoded_content_inspector import EncodedContentInspector


def locate(args: argparse.Namespace) -> Path:
    if args.pdf:
        path = Path(args.pdf).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise ValueError("Arquivo PDF não encontrado")
        return path
    wanted = args.sha.lower()
    if len(wanted) != 64 or any(c not in "0123456789abcdef" for c in wanted):
        raise ValueError("SHA-256 inválido")
    root = Path("storage/uploads")
    if not root.exists():
        raise ValueError("Pasta storage/uploads não encontrada; use --pdf")
    for path in root.glob("*.pdf"):
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest().lower() == wanted:
            return path.resolve()
    raise ValueError("PDF com o SHA solicitado não localizado em storage/uploads")


def main() -> int:
    p = argparse.ArgumentParser()
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha", help="SHA-256 do PDF em storage/uploads")
    target.add_argument("--pdf", help="Caminho do PDF")
    p.add_argument("--with-barcodes", action="store_true", help="Lê códigos pelo BarcodeReader existente")
    args = p.parse_args()
    try:
        path = locate(args)
        barcodes = []
        if args.with_barcodes:
            from app.domain.readers.barcode_reader import BarcodeReader
            barcodes = BarcodeReader().read(str(path))
        results = QrStructuralInspector().inspect_pdf(str(path), barcodes=barcodes)
        semantic_inputs = EncodedContentInspector().prepare_qr_semantic_inputs(barcodes)
    except Exception as exc:
        print(f"Diagnóstico interrompido: {type(exc).__name__}: {exc}")
        return 1
    print("=" * 70)
    print("DOCDNA | CF-QA 003.9.1 | FONTES QR E CONTEÚDO CODIFICADO")
    print("Somente leitura. Coordenadas em PONTOS PDF. Sem conclusão de fraude.")
    print(f"Arquivo: {path}")
    print(f"Candidatos agrupados: {len(results)} | barcodes fornecidos: {len(barcodes)}")
    for i, item in enumerate(results, 1):
        print("-" * 70)
        print(f"#{i} {item['code']} | página={item['page_number']} | fonte={item['font_name']}")
        print(f"Caixa PDF: {item['bounding_box_pdf_points']} | fragmentos={item['span_count']}")
        print(f"Total de caracteres: {item['raw_length']} | sha256: {item['raw_sha256']}")
        print(f"QRs associados geometricamente: {len(item['linked_qr_codes'])}")
        for match in item["linked_qr_codes"]:
            print(f"  - índice: {match['barcode_index']} | hash payload: {match['content_sha256']}")
        print(f"Trechos de texto decodificado: {len(item['decoded_content'])}")
        for decoded in item["decoded_content"][:2]:
            # Minimiza a exposição de dados do documento no terminal.
            print(f"  - codificação: {decoded['encoding_chain']} | bytes={decoded['byte_length']}")
            print(f"    SHA-256 do texto: {decoded['sha256']}")
    print(f"Payloads QR encaminháveis à análise semântica: {len(semantic_inputs)}")
    print("=" * 70)
    print("ATENÇÃO: associação espacial não comprova mesmo payload nem ocultação visual.")
    print("Textos decodificados exigem futura análise semântica independente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
