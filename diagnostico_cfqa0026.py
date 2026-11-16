"""Diagnostico CF-QA 002.6 (somente leitura; nao modifica arquivos).

Salve este arquivo na raiz do projeto DocDNA e execute:
    python diagnostico_cfqa0026.py

Mostra qual detector o Python importou e quais etapas impedem/permitem
que uma linha de arrecadacao com cabecalho invalido gere evidencia.
O caso eh SINTETICO e nao valida os PDFs reais.
"""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

from app.domain.detectors.barcode_numeric_line_detector import (
    BarcodeNumericLineDetector,
)
from app.domain.rules.numeric_line_validator import NumericLineValidator


def _print_stage(name: str, value) -> None:
    print(f"  {name}: {value}")


def main() -> int:
    cls = BarcodeNumericLineDetector
    source = Path(inspect.getfile(cls)).resolve()
    source_text = source.read_text(encoding="utf-8-sig")
    normalized_text = source_text.replace("\r\n", "\n")
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    print("=" * 67)
    print("DOCDNA | Diagnostico da versao REAL do detector - CF-QA 002.6")
    print("=" * 67)
    _print_stage("Arquivo importado", source)
    _print_stage("SHA-256 (texto com quebras normalizadas)", digest)

    detector = cls()
    method_name = "_nearby_itf_geometry_confidence"
    has_method = callable(getattr(detector, method_name, None))
    _print_stage("Metodo de geometria ITF presente", has_method)
    if not has_method:
        print("\nBLOQUEIO: detector importado ainda nao inclui o CF-QA 002.6.")
        print("Substitua app/domain/detectors/barcode_numeric_line_detector.py")
        print("pelo arquivo completo verificado e repita este diagnostico.")
        return 2

    # Teste sintetico: 48 digitos com identificador de referencia impossivel.
    digits = "835" + "1" * 45
    validation = NumericLineValidator().validate(
        SimpleNamespace(line_index=1, normalized_content=digits)
    )
    location = SimpleNamespace(
        line_index=1, page_number=1, matched_content=digits,
        located=True, confidence=0.99,
        left=210, top=105, width=370, height=20,
    )
    itf = SimpleNamespace(
        barcode_index=7, page_number=1, content="8468" + "0" * 40,
        format="ITF",
        location=SimpleNamespace(
            page_number=1,
            bounding_box=SimpleNamespace(x=105, y=58, width=240, height=52),
        ),
    )
    context = SimpleNamespace(
        numeric_line_validations=[validation],
        numeric_line_locations=[location],
        ocr_text_boxes=[SimpleNamespace(
            page_number=1, text="Conta do cliente", confidence=0.99,
            left=20, top=102, width=165, height=22,
        )],
        barcodes=[itf],
    )
    reason = detector._structural_invalidity_reason(validation)
    trusted = detector._unique_trusted_location(context, validation)
    label = detector._nearby_payment_label_confidence(
        context=context, location=location
    )
    geometry = detector._nearby_itf_geometry_confidence(
        context=context, location=location, validation=validation
    )
    codes = [item.code for item in detector.analyze(context)]

    print("\nCENARIO SINTETICO (nao representa resultado dos PDFs):")
    _print_stage("Status do validador", validation.status)
    _print_stage("Justificativa estrutural", reason)
    _print_stage("Localizacao confiavel", trusted is not None)
    _print_stage("Rotulo de pagamento proximo", label)
    _print_stage("Proximidade geometrica ITF", geometry)
    _print_stage("Codigos de evidencias produzidas", codes)

    expected_code = "PAYMENT_LINE_INVALID_STRUCTURE"
    if expected_code in codes:
        print("\nGREEN SINTETICO: o detector importado reconheceu o caso.")
        print("Se o pytest falhar, confira se o arquivo de testes eh o corrigido.")
        return 0
    print("\nRED: o detector carregado nao produziu a evidencia esperada.")
    print("Envie o texto deste diagnostico para localizar o bloqueio exato.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
