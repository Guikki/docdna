"""CF-QA 002.7 — confere o contexto REAL montado pelo DocDNA.

Colocar na raiz do projeto e executar com:
    python diagnostico_cfqa0027_contexto_real.py
    python diagnostico_cfqa0027_contexto_real.py --todos

Diferenca em relacao ao teste anterior: este script NAO inventa nem remonta
localizacoes a partir do Excel. Ele chama AnalysisContextBuilder.build() com o
PDF original, ou seja, usa as MESMAS etapas e objetos de contexto que deveriam
ser disponibilizados ao detector na analise normal.

Pode gerar artefatos de extracao/anotacao na pasta configurada em settings.
Nao altera arquivos-fonte, regras de risco, Excel ou banco de dados.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.domain.builders.analysis_context_builder import AnalysisContextBuilder
from app.domain.detectors.barcode_numeric_line_detector import BarcodeNumericLineDetector
from app.domain.models.document import Document
from app.domain.shared.enums import DocumentStatus

EXPECTED = (
    {
        "name": "0005510-67.2026.8.16.0064.pdf",
        "stored": "0e940cc9-b9e3-4323-b227-ab9d863ae886.pdf",
        "sha": "0fe8269792a5994ea1dd7f3651903f2410208188a9ca6a24659ea5980b258b53",
        "line": "835271604927490638172754217954806473963407251884",
    },
    {
        "name": "0006078-36.2026.8.16.0112.pdf",
        "stored": "05ac930a-39e0-4256-900b-1548adc5c687.pdf",
        "sha": "7bb5e20cb9f857fa38071d164bc3ffdc85e72b0d0db87be9e75763757c46c9d5",
        "line": "835271604927490638172754217954806473963407251884",
    },
    {
        "name": "4002640-82.2026.8.26.0296.pdf",
        "stored": "1c678e4a-1ce1-4b18-9c03-59444afed194.pdf",
        "sha": "6d98de1f37ff20a0c3e8bc373f28d59f3b28174c28a699693cd8d68c4112befd",
        "line": "583914726405271638950427846205371694394781620538",
    },
)
CODE = "PAYMENT_LINE_INVALID_STRUCTURE"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_file(item: dict, root: Path) -> Path:
    direct = root / "storage" / "uploads" / item["stored"]
    if direct.is_file() and file_sha256(direct) == item["sha"]:
        return direct
    # Busca por HASH, nao confunde nomes CNJ diferentes com identidade de PDF.
    uploads = root / "storage" / "uploads"
    for candidate in uploads.glob("*.pdf"):
        try:
            if file_sha256(candidate) == item["sha"]:
                return candidate
        except OSError:
            continue
    raise FileNotFoundError(
        f"PDF nao localizado em storage/uploads (SHA-256 {item['sha']})"
    )


def digits(s) -> str:
    return "".join(ch for ch in str(s or "") if "0" <= ch <= "9")


def print_barcode_locations(context, detector, page: int) -> None:
    barcodes = list(getattr(context, "barcodes", ()) or ())
    print(f"  Barcodes DENTRO do AnalysisContext: {len(barcodes)}")
    payment = detector._payment_barcodes_on_page(context=context, page_number=page)
    print(f"  ITFs 44 digitos na pagina {page}: {len(payment)}")
    for barcode in payment:
        obj = getattr(barcode, "location", None)
        box = getattr(obj, "bounding_box", None)
        if box is None:
            print("    - ITF sem bounding_box no contexto (bloqueia geometria).")
        else:
            print(
                "    - ITF bounding_box (pontos PDF): "
                f"x={box.x}, y={box.y}, w={box.width}, h={box.height}"
            )


def check_item(item: dict, root: Path) -> bool:
    print("\n" + "=" * 78)
    print("DOCUMENTO:", item["name"])
    pdf = locate_file(item, root)
    print("PDF:", pdf)
    print("SHA-256 original: OK")

    # A classe Document e a mesma usada pelo UploadDocumentUseCase.
    doc = Document(
        id=uuid4(),
        original_filename=item["name"],
        stored_filename=pdf.name,
        saved_path=str(pdf),
        extension=".pdf",
        mime_type="application/pdf",
        size_bytes=pdf.stat().st_size,
        sha256=item["sha"],
        uploaded_at=datetime.now(),
        status=DocumentStatus.RECEIVED,
    )

    print("Construindo contexto REAL (pode executar OCR e evidencias visuais)...")
    builder = AnalysisContextBuilder()
    context = builder.build(doc)
    detector = BarcodeNumericLineDetector()

    validations = [
        obj for obj in (getattr(context, "numeric_line_validations", []) or [])
        if digits(getattr(obj, "normalized_content", "")) == item["line"]
    ]
    print("  Validacoes da linha esperada no CONTEXTO real:", len(validations))
    if not validations:
        print("BLOQUEIO CONFIRMADO: a linha nao foi recuperada pelo pipeline de extracao.")
        return False

    any_evidence = False
    for validation in validations:
        print("\n  Linha / indice:", validation.line_index)
        print("  Status:", getattr(validation, "status", None))
        reason = detector._structural_invalidity_reason(validation)
        print("  Motivo estrutural:", reason)
        locs = [
            loc for loc in (getattr(context, "numeric_line_locations", []) or [])
            if getattr(loc, "line_index", None) == validation.line_index
        ]
        print("  Localizacoes para este indice:", len(locs))
        for loc in locs:
            print(
                "    - located=", getattr(loc, "located", None),
                "pagina=", getattr(loc, "page_number", None),
                "confianca=", getattr(loc, "confidence", None),
                "digitos=", len(digits(getattr(loc, "matched_content", ""))),
                "retangulo=", (
                    getattr(loc, "left", None), getattr(loc, "top", None),
                    getattr(loc, "width", None), getattr(loc, "height", None)
                ),
            )
        trusted = detector._unique_trusted_location(context, validation)
        print("  Localizacao integral confiavel no CONTEXTO:", trusted is not None)
        if trusted is None:
            print("  BLOQUEIO: segmento visual/ambiguidades/confianca do contexto.")
            continue
        page = trusted.page_number
        print_barcode_locations(context, detector, page)
        label_conf = detector._nearby_payment_label_confidence(context=context, location=trusted)
        geo_conf = detector._nearby_itf_geometry_confidence(
            context=context, location=trusted, validation=validation
        )
        print("  Confianca rotulo OCR:", label_conf)
        print("  Confianca proximidade ITF:", geo_conf)
        if reason and label_conf is None and geo_conf is None:
            print("  BLOQUEIO: sem contexto financeiro espacial elegivel no builder REAL.")

    evidences = detector.analyze(context)
    produced_codes = [e.code for e in evidences]
    any_evidence = CODE in produced_codes
    print("\n  Evidencias do detector com contexto REAL:", produced_codes)
    if any_evidence:
        print("RESULTADO: alerta GERADO pelo builder + detector REAL.")
        print("PROXIMA INVESTIGACAO: UploadDocumentUseCase, fluxo de lote, cache ou exportacao.")
    else:
        print("RESULTADO: alerta NAO gerado pelo builder + detector REAL.")
        print("CORRIGIR: o bloqueio detalhado acima, ANTES do upload/exportacao.")
    return any_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico do contexto REAL CF-QA 002.7")
    parser.add_argument("--todos", action="store_true", help="Executar nos tres PDFs (padrao: primeiro)")
    args = parser.parse_args()
    root = Path.cwd()
    if not (root / "app").is_dir():
        print("ERRO: execute a partir da raiz do projeto docdna, com a .venv ativa.")
        return 2
    targets = EXPECTED if args.todos else EXPECTED[:1]
    status = []
    for item in targets:
        try:
            status.append(check_item(item, root))
        except Exception as exc:
            print(f"ERRO AO RECONSTRUIR CONTEXTO: {type(exc).__name__}: {exc}")
            raise
    print("\n" + "=" * 78)
    print("CONTEXTO REAL:", sum(status), "alerta(s) /", len(status), "documento(s)")
    print("Sem conclusao de cobertura definitiva ate conferir o fluxo de upload e o Excel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
