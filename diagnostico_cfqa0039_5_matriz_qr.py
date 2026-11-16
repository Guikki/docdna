"""CF-QA 003.9.5 — diagnóstico de matriz QR em PDFs reais (somente leitura).

Usar na raiz do DocDNA:
    python diagnostico_cfqa0039_5_matriz_qr.py --sha <SHA-256>
    python diagnostico_cfqa0039_5_matriz_qr.py --pdf "caminho/arquivo.pdf"

Não altera arquivos nem persistência, não executa conteúdo de QR, não
classifica fraude/ocultação e não altera o fluxo de Prompt Injection.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.services.qr_matrix_inspector import QrMatrixInspector
from app.domain.services.qr_structural_inspector import QrStructuralInspector


def locate(path: str | None, sha: str | None) -> Path:
    if path:
        result = Path(path).expanduser().resolve()
        if result.suffix.lower() != ".pdf" or not result.is_file():
            raise ValueError("PDF não encontrado")
        return result
    expected = (sha or "").casefold()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("SHA-256 inválido")
    for pdf in Path("storage/uploads").glob("*.pdf"):
        digest = hashlib.sha256()
        with pdf.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() == expected:
            return pdf.resolve()
    raise FileNotFoundError("PDF não localizado em storage/uploads")


def decode_with_existing_opencv(rows: tuple[str, ...]) -> tuple[str, str | None]:
    """Tentativa opcional local; retorna SHA, nunca executa ou imprime payload."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return "DECODER_UNAVAILABLE", None
    # 1 representa módulo escuro. Quiet zone de 4 módulos.
    array = np.array([[0 if ch == "1" else 255 for ch in row] for row in rows], dtype=np.uint8)
    bordered = np.pad(array, 4, mode="constant", constant_values=255)
    enlarged = cv2.resize(bordered, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    try:
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(enlarged)
    except (cv2.error, ValueError):
        return "DECODE_FAILED", None
    if not isinstance(decoded, str) or not decoded:
        return "NO_DECODE", None
    return "DECODED", hashlib.sha256(decoded.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha")
    target.add_argument("--pdf")
    args = parser.parse_args()
    try:
        import pymupdf
        path = locate(args.pdf, args.sha)
        barcodes = BarcodeReader().read(str(path))
        structural = QrStructuralInspector()
        matrix = QrMatrixInspector()
        print("=" * 72)
        print("DOCDNA | CF-QA 003.9.5 — Validação matricial QR (somente leitura)")
        print("Não altera classificações, não declara ocultação nem fraude.")
        print(f"PDF: {path.name} | Códigos lidos: {len(barcodes)}")
        total_groups = 0
        with pymupdf.open(str(path)) as document:
            for page_number, page in enumerate(document, start=1):
                if page_number > structural.MAX_PAGES:
                    break
                candidates = structural._candidate_spans(page, page_number)
                groups = structural._group(candidates)
                for group in groups[:structural.MAX_GROUPS_PER_PAGE]:
                    total_groups += 1
                    old = structural._record(group, list(barcodes))
                    finding = matrix.inspect_group(group)
                    print("-" * 72)
                    print(f"Grupo {total_groups} | Página {page_number} | Fonte {group.get('font_name')}")
                    print(f"Correlação anterior: {old.get('code')} | QR(s) próximos: {len(old.get('linked_qr_codes', []))}")
                    print(f"Fragmentos: {finding['fragment_count']} | Bits: {finding['bit_count']} | Tamanhos: {finding['fragment_lengths']}")
                    print(f"Matriz: {finding['dimension']} x {finding['dimension']} | Versão: {finding['version']}")
                    print(f"Reconstrução: {finding['reconstruction_method']}")
                    print(f"Validação: {finding['status']} | {finding['reason']}")
                    if finding['matrix_structurally_validated']:
                        print(f"Orientação: {finding['orientation']} | Bits invertidos: {finding['inverted']}")
                        print(f"Máscara: {finding['mask_pattern']} | Correção de erros: {finding['error_correction_level']}")
                        rows = matrix.normalized_rows(group, finding)
                        if rows is not None:
                            decode_status, decoded_sha = decode_with_existing_opencv(rows)
                            print(f"Decodificação adicional via OpenCV: {decode_status}")
                            if decoded_sha:
                                associated = [r.get('content_sha256') for r in old.get('linked_qr_codes', [])]
                                if associated:
                                    match = "IGUAL" if decoded_sha in associated else "DIFERENTE (revisar)"
                                    print(f"Comparação exata com QR visual associado: {match}")
                                else:
                                    print("Comparação com QR visual: SEM ASSOCIAÇÃO GEOMÉTRICA")
                    print("Ocultação visual: NÃO DETERMINADA | Prompt Injection: NÃO ALTERADO")
        print("=" * 72)
        print(f"Total de grupos examinados: {total_groups}")
        print("Validação estrutural não equivale a decodificação nem prova ocultação.")
        return 0
    except Exception as error:
        print(f"Diagnóstico interrompido: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
