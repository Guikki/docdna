"""CF-QA 003.9.2 — verifica a integração QR estrutural + semântica.

Somente leitura. Não grava análises, não inicia servidor, não abre URLs,
não executa payloads de QR Code, não envia texto a modelos externos.

    python diagnostico_cfqa0039_2_semantica.py --sha <sha256>
    python diagnostico_cfqa0039_2_semantica.py --pdf "arquivo.pdf"
"""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from app.domain.document.adapters.native_document_adapter import NativeDocumentAdapter
from app.domain.prompt_injection.detectors.tiny_text_detector import TinyTextDetector
from app.domain.prompt_injection.services.prompt_injection_analysis_service import (
    PromptInjectionAnalysisService,
)
from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.services.qr_structural_inspector import QrStructuralInspector


def locate(path: str | None, sha: str | None) -> Path:
    if path:
        result = Path(path).expanduser().resolve()
        if result.suffix.lower() != ".pdf" or not result.is_file():
            raise ValueError("PDF não encontrado")
        return result
    expected = (sha or "").casefold()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("SHA-256 inválido")
    root = Path("storage/uploads")
    for pdf in root.glob("*.pdf"):
        digest = hashlib.sha256()
        with pdf.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() == expected:
            return pdf.resolve()
    raise FileNotFoundError("Arquivo não localizado em storage/uploads")


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha")
    target.add_argument("--pdf")
    args = parser.parse_args()
    try:
        path = locate(args.pdf, args.sha)
        barcodes = BarcodeReader().read(str(path))
        normalized = NativeDocumentAdapter().adapt(source=str(path))
        structural = QrStructuralInspector().inspect_pdf(str(path), barcodes=barcodes)
        # Comparação bruta do tiny_text, antes da consolidação de evidências.
        detector = TinyTextDetector()
        raw_tiny = sum(len(detector.detect(spans=page.text_spans))
                       for page in normalized.pages)
        assessment = PromptInjectionAnalysisService().analyze(
            normalized_document=normalized,
            barcodes=barcodes,
            qr_structural_findings=structural,
        )
    except Exception as error:
        print(f"Diagnóstico interrompido: {type(error).__name__}: {error}")
        return 1

    evidences = tuple(getattr(assessment, "evidences", ()) or ())
    codes = Counter(str(getattr(e, "code", "")) for e in evidences)
    sources = Counter(str(getattr(e, "metadata", {}).get("source", ""))
                      for e in evidences)
    print("=" * 72)
    print("DOCDNA | CF-QA 003.9.2 — QR estrutural e inspeção semântica")
    print("Somente leitura; não declara autenticidade, fraude nem QR oculto.")
    print(f"PDF: {path.name} | Códigos lidos: {len(barcodes)}")
    print(f"Grupos estruturais: {len(structural)}")
    for index, item in enumerate(structural, 1):
        print(f"Grupo {index}: {item['code']} | página={item['page_number']} "
              f"| fonte={item['font_name']} | fragmentos={item['span_count']} "
              f"| QR(s) próximos={len(item['linked_qr_codes'])} "
              f"| textos recuperados={len(item['decoded_content'])}")
    print("-" * 72)
    print(f"Tiny text bruto, sem correlação: {raw_tiny}")
    print(f"Tiny text após integração: {codes.get('PROMPT_INJECTION_TINY_TEXT', 0)}")
    print(f"Total de evidências semânticas e tipográficas: {len(evidences)}")
    print("Códigos de evidência:")
    for code, amount in sorted(codes.items()):
        print(f"  {code}: {amount}")
    print("Origens:")
    for source, amount in sorted(sources.items()):
        print(f"  {source or '(sem fonte)'}: {amount}")
    print("=" * 72)
    print("A ausência de alertas de Prompt Injection não comprova ausência de ataque.")
    print("A associação espacial não prova igualdade de payload nem ocultação visual.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
