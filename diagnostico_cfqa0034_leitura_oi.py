"""CF-QA 003.4 — diagnóstico de decodificação real, somente leitura.

Uso:
    python diagnostico_cfqa0034_leitura_oi.py
    python diagnostico_cfqa0034_leitura_oi.py "C:\\caminho\\para\\fatura.pdf"

Sem argumento, procura pelo SHA-256 do PDF Oi fornecido no checkpoint,
primeiro na raiz do projeto e depois em storage/uploads. Não altera PDF,
repositórios nem o resultado dos lotes anteriores.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pymupdf

from app.domain.readers.barcode_reader import BarcodeReader


REFERENCE_FILENAME = "0802054-81.2021.8.10.0076.pdf"
REFERENCE_SHA256 = "5e5c5318d8246230b4de448a0a3b3bc03496eafb524c8c6eb64649bd5e951920"
REFERENCE_SIZE = 1_582_717


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_sample() -> Path | None:
    direct = Path(REFERENCE_FILENAME)
    if direct.is_file() and file_hash(direct) == REFERENCE_SHA256:
        return direct

    folder = Path("storage/uploads")
    if not folder.exists():
        return None
    for candidate in folder.rglob("*.pdf"):
        try:
            if candidate.stat().st_size != REFERENCE_SIZE:
                continue
            if file_hash(candidate) == REFERENCE_SHA256:
                return candidate
        except OSError:
            continue
    return None


def is_payment_itf(barcode) -> bool:
    fmt = str(barcode.format).upper().replace("_", "").replace("-", "")
    text = str(barcode.content).strip()
    return (fmt == "ITF" or fmt.endswith(".ITF")) and text.isascii() and text.isdigit() and len(text) == 44 and text.startswith("8")


def main() -> int:
    if len(sys.argv) > 2:
        print('Uso: python diagnostico_cfqa0034_leitura_oi.py ["caminho\\arquivo.pdf"]')
        return 2

    source = Path(sys.argv[1]) if len(sys.argv) == 2 else find_sample()
    if source is None or not source.is_file():
        print("PDF da Oi não encontrado automaticamente em storage/uploads.")
        print('Execute: python diagnostico_cfqa0034_leitura_oi.py "C:\\caminho\\fatura.pdf"')
        return 2

    print("=" * 75)
    print("DOCDNA - CF-QA 003.4 | LEITURA REAL DOS CÓDIGOS (SOMENTE LEITURA)")
    print("=" * 75)
    print("Arquivo:", source.resolve())
    sha = file_hash(source)
    print("SHA-256:", sha)
    print("É a amostra de referência:", "SIM" if sha == REFERENCE_SHA256 else "NÃO")

    with pymupdf.open(source) as doc:
        print("Páginas:", len(doc))

    try:
        readings = BarcodeReader().read(str(source))
    except Exception as exc:
        print(f"FALHA NA DECODIFICAÇÃO: {type(exc).__name__}: {exc}")
        return 1

    print("Total de códigos decodificados:", len(readings))
    full_itfs = 0
    for barcode in readings:
        content = str(barcode.content or "")
        full = is_payment_itf(barcode)
        if full:
            full_itfs += 1
        loc = barcode.location
        bbox = getattr(loc, "bounding_box", None)
        coords = (
            f"x={bbox.x:.1f}, y={bbox.y:.1f}, "
            f"w={bbox.width:.1f}, h={bbox.height:.1f}"
            if bbox is not None else "não disponível"
        )
        print("-" * 75)
        print(f"Código #{barcode.barcode_index} | página {barcode.page_number}")
        print("Formato:", barcode.format)
        print("Conteúdo:", content)
        print("Comprimento:", len(content))
        print("Região (pontos PDF):", coords)
        print("Hash da região:", barcode.image_hash or "não disponível")
        print("Candidato a ITF de 44 dígitos:", "SIM (ainda não validado)" if full else "NÃO")

    print("=" * 75)
    print("ITFs com formato de arrecadação de 44 dígitos:", full_itfs)
    if full_itfs == 0:
        print("RESULTADO: leitura de cobrança integral ainda NÃO demonstrada.")
    else:
        print("RESULTADO: houve decodificação de ITF de 44 dígitos; validar o conteúdo e os DVs.")
    print("Este diagnóstico não atesta autenticidade nem fraude.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
