"""DocDNA CF-QA 002.6 — diagnóstico dos 3 PDFs reais (SOMENTE LEITURA).

Uso, na raiz do projeto (com .venv ativo):

    python diagnostico_cfqa0026_pdfs_reais.py

O script procura PDFs pelo hash SHA-256 informado pela exportação e914/53cc.
Se não os localizar no projeto, informe a pasta que os contém:

    python diagnostico_cfqa0026_pdfs_reais.py --pasta "C:\\caminho\\dos\\pdfs"

Também aceita os caminhos de PDFs individuais:

    python diagnostico_cfqa0026_pdfs_reais.py "C:\\caminho\\arquivo1.pdf" "C:\\caminho\\arquivo2.pdf"

Não modifica o código, o banco de dados ou os PDFs.
A reprodução usa localizações registradas NO XLSX do lote 53ccfbb9 e
relê os códigos de barras dos PDFs originais. Não é a execução integral
original do pipeline; serve para separar as causas do bloqueio.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
from types import SimpleNamespace

from app.domain.detectors.barcode_numeric_line_detector import BarcodeNumericLineDetector
from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.rules.numeric_line_validator import NumericLineValidator


# Dados copiados da planilha docdna_lote_53ccfbb9.xlsx (03/11/2026).
# São expectativas de DIAGNÓSTICO, não regras implementadas no DocDNA.
AMOSTRAS = [
    {
        "nome": "0005510-67.2026.8.16.0064.pdf",
        "sha256": "0fe8269792a5994ea1dd7f3651903f2410208188a9ca6a24659ea5980b258b53",
        "bytes": 99093,
        "indice": 2,
        "linha": "835271604927490638172754217954806473963407251884",
        "localizado": "835271604927490638172754217954806473963407251884",
        "retangulo": (180, 1523, 504, 11),
    },
    {
        "nome": "0006078-36.2026.8.16.0112.pdf",
        "sha256": "7bb5e20cb9f857fa38071d164bc3ffdc85e72b0d0db87be9e75763757c46c9d5",
        "bytes": 99405,
        "indice": 2,
        "linha": "835271604927490638172754217954806473963407251884",
        "localizado": "835271604927490638172754217954806473963407251884",
        "retangulo": (180, 1523, 504, 11),
    },
    {
        "nome": "4002640-82.2026.8.26.0296.pdf",
        "sha256": "6d98de1f37ff20a0c3e8bc373f28d59f3b28174c28a699693cd8d68c4112befd",
        "bytes": 91068,
        "indice": 1,
        "linha": "583914726405271638950427846205371694394781620538",
        "localizado": "58391472640527163895042784620537169439478162053",
        "retangulo": (167, 1546, 519, 12),
    },
]

EXCLUDED_FOLDERS = {".venv", "venv", ".git", ".idea", ".pytest_cache", "node_modules", "__pycache__", "dist", "build"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1_048_576):
            digest.update(block)
    return digest.hexdigest()


def find_pdf_files(roots: list[Path], supplied: list[Path]) -> dict[str, Path]:
    remaining = {a["sha256"]: a for a in AMOSTRAS}
    results: dict[str, Path] = {}

    def accept(path: Path) -> None:
        try:
            if not path.is_file() or path.suffix.lower() != ".pdf":
                return
            size = path.stat().st_size
            if not any(a["bytes"] == size for a in remaining.values()):
                return
            signature = sha256_of(path)
        except (OSError, PermissionError):
            return
        if signature in remaining:
            results[signature] = path.resolve()
            remaining.pop(signature)

    for path in supplied:
        accept(path)
    for root in roots:
        if not remaining:
            break
        if not root.is_dir():
            continue
        for directory, subdirs, filenames in os.walk(root):
            subdirs[:] = [d for d in subdirs if d not in EXCLUDED_FOLDERS]
            for name in filenames:
                if name.lower().endswith(".pdf"):
                    accept(Path(directory, name))
            if not remaining:
                break
    return results


def analyze_geometry(detector, location, itfs) -> None:
    """Mostra separadamente os mesmos filtros geométricos do detector."""
    ax1, ay1, width, height = (
        location.left, location.top, location.width, location.height
    )
    ax2, ay2 = ax1 + width, ay1 + height
    print(f"  Localização OCR do XLSX: x={ax1}, y={ay1}, largura={width}, altura={height} (escala 2x)")
    if not itfs:
        print("  BLOQUEIO: nenhum ITF de 44 dígitos foi decodificado na mesma página.")
        return

    contents = set()
    applicable = 0
    for index, barcode in enumerate(itfs, start=1):
        contents.add(detector._normalize_digits(barcode.content))
        loc = getattr(barcode, "location", None)
        rect = getattr(loc, "bounding_box", None)
        print(f"  ITF {index}: índice={barcode.barcode_index}; formato={barcode.format}; página={barcode.page_number}")
        print(f"      Conteúdo: {barcode.content}")
        if rect is None:
            print("      BLOQUEIO: leitor de barras não forneceu bounding_box/localização.")
            continue
        try:
            # Mesma regra do CF-QA 002.6: ZXing em pontos PDF, OCR em 2x.
            x, y, w, h = (float(rect.x)*2, float(rect.y)*2, float(rect.width)*2, float(rect.height)*2)
            if not all(math.isfinite(n) for n in (x, y, w, h)) or x < 0 or y < 0 or w <= 0 or h <= 0:
                print("      BLOQUEIO: geometria inválida (não finita, negativa ou sem área).")
                continue
        except (TypeError, ValueError, AttributeError):
            print("      BLOQUEIO: bounding_box não tem as coordenadas numéricas esperadas.")
            continue
        overlap = max(0.0, min(ax2, x+w) - max(ax1, x))
        ratio = overlap / min(width, w) if min(width, w) > 0 else 0
        gap = max(0.0, y - ay2, ay1 - (y+h))
        passes = ratio >= 0.35 and gap <= 160
        print(f"      ITF convertido para escala OCR 2x: x={x:.1f}, y={y:.1f}, largura={w:.1f}, altura={h:.1f}")
        print(f"      Sobreposição horizontal={ratio:.3f} (mín. 0.350); distância vertical={gap:.1f} (máx. 160)")
        print(f"      {'PASSA' if passes else 'BLOQUEIO'}: filtro espacial")
        if passes:
            applicable += 1

    if applicable == 0:
        print("  CAUSA GEOMÉTRICA: nenhum ITF passou pelos limites de proximidade.")
    elif len(contents) > 1:
        print("  VERIFICAR: há conteúdos ITF distintos; o detector exige ausência de ambiguidade.")


def check_sample(sample: dict, path: Path) -> None:
    print("\n" + "=" * 76)
    print("DOCUMENTO:", sample["nome"])
    print("PDF confirmado por SHA-256:", path)
    print("=" * 76)

    try:
        barcodes = BarcodeReader().read(str(path))
    except Exception as exc:
        print(f"ERRO na leitura real de barras: {type(exc).__name__}: {exc}")
        return

    detector = BarcodeNumericLineDetector()
    validation = NumericLineValidator().validate(SimpleNamespace(
        line_index=sample["indice"], normalized_content=sample["linha"]
    ))
    x, y, w, h = sample["retangulo"]
    location = SimpleNamespace(
        line_index=sample["indice"], page_number=1,
        matched_content=sample["localizado"],
        located=True, confidence=1.0,
        left=x, top=y, width=w, height=h,
    )
    context = SimpleNamespace(
        numeric_line_validations=[validation],
        numeric_line_locations=[location],
        ocr_text_boxes=[],  # Rótulos OCR NÃO são reconstruídos neste diagnóstico.
        barcodes=barcodes,
    )
    reason = detector._structural_invalidity_reason(validation)
    trusted = detector._unique_trusted_location(context, validation)
    itfs = detector._payment_barcodes_on_page(context=context, page_number=1)
    confidence = detector._nearby_itf_geometry_confidence(
        context=context, location=location, validation=validation
    )
    print("Validação:", str(validation.status))
    print("Motivo estrutural:", reason)
    print("Linha reconhecida:", sample["linha"], f"({len(sample['linha'])} dígitos)")
    print("Trecho visual exportado:", sample["localizado"], f"({len(sample['localizado'])} dígitos)")
    print("Localização integral confiável:", trusted is not None)
    print("Total de códigos lidos:", len(barcodes), "| ITFs de pagamento na página 1:", len(itfs))
    analyze_geometry(detector, location, itfs)
    print("Confiança do método espacial:", confidence)
    try:
        codes = [e.code for e in detector.analyze(context)]
        print("Evidências reproduzidas SEM caixas OCR de rótulos:", codes)
    except Exception as exc:
        print("ERRO no teste isolado de evidências:", type(exc).__name__, exc)
    if trusted is None:
        print("CONCLUSÃO: localização visual não confirma todos os dígitos; a regra atual NÃO pode emitir o alerta.")
    elif confidence is None:
        print("CONCLUSÃO: localização integral existe; verificar o BLOQUEIO de geometria ITF descrito acima.")
    else:
        print("CONCLUSÃO: a geometria relida permite o alerta nesta reprodução. Se a análise real não alertou,")
        print("revisar a diferença entre o contexto persistido e esta leitura, especialmente posições do barcode.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", nargs="*", help="PDFs originais, se disponíveis")
    parser.add_argument("--pasta", help="Pasta adicional onde procurar os PDFs originais")
    args = parser.parse_args()

    roots = [Path.cwd()]
    if args.pasta:
        roots.insert(0, Path(args.pasta))
    found = find_pdf_files(roots, [Path(p) for p in args.pdfs])
    print("DOCDNA - CF-QA 002.6 / PDFs reais / somente leitura")
    print("Amostras esperadas:", len(AMOSTRAS), "| Localizadas por SHA-256:", len(found))
    for sample in AMOSTRAS:
        path = found.get(sample["sha256"])
        if path:
            check_sample(sample, path)
        else:
            print("\nPDF NÃO ENCONTRADO:", sample["nome"])
            print("  SHA-256 esperado:", sample["sha256"])
    if len(found) < len(AMOSTRAS):
        print("\nSe os PDFs não estiverem dentro do projeto, execute com --pasta")
        print('Ex.: python diagnostico_cfqa0026_pdfs_reais.py --pasta "C:\\Users\\...\\PDFs"')
        print("Os dados de PDFs não encontrados NÃO foram validados por este script.")
        return 2
    print("\nDIAGNÓSTICO CONCLUÍDO. Este teste não substitui a análise integral dos originais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
