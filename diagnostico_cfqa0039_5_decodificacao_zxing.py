"""DocDNA CF-QA 003.9.5 — diagnóstico somente de leitura do núcleo QR.

Objetivos:
* Verificar as DUAS cópias reais dos 15 bits de formato, sem misturá-las.
* Discriminar os seis padrões de alinhamento da matriz 57x57.
* Tentar decodificar com o ZXing, já utilizado pelo BarcodeReader do DocDNA.
* Comparar o SHA-256 do texto decodificado com o QR lido na página.

Não altera PDFs, dados persistidos, classificações, Prompt Injection ou
ocultação visual. Não imprime bits nem payloads. Testa apenas a hipótese
matricial, sem afirmar ocultação, autenticidade ou fraude.

Na raiz do projeto (requer os diagnósticos anteriores na mesma pasta):
    python diagnostico_cfqa0039_5_decodificacao_zxing.py --sha HASH_64_HEX
    python diagnostico_cfqa0039_5_decodificacao_zxing.py --pdf "caminho.pdf"
"""
from __future__ import annotations

import argparse
import hashlib
from typing import Any


def _read_format_copies(rows: tuple[str, ...]) -> tuple[int, int]:
    """Lê cópia superior-esquerda e cópia direita/inferior separadamente.

    A ordem dos 15 bits segue a atribuição (menos significativo primeiro)
    do formato QR Model 2. Contrasta com leituras híbridas das duas regiões.
    """
    n = len(rows)
    if n < 21 or any(len(row) != n or set(row) - {"0", "1"} for row in rows):
        raise ValueError("Matriz inválida para formato QR")

    first = (
        [(8, i) for i in range(6)]
        + [(8, 7), (8, 8), (7, 8)]
        + [(14 - i, 8) for i in range(9, 15)]
    )
    second = (
        [(n - 1 - i, 8) for i in range(8)]
        + [(8, n - 15 + i) for i in range(8, 15)]
    )

    def read(positions: list[tuple[int, int]]) -> int:
        return sum((rows[y][x] == "1") << i for i, (x, y) in enumerate(positions))

    return read(first), read(second)


def _format_candidates(word: int, inspector_cls: Any) -> list[dict[str, Any]]:
    result = []
    for payload in range(32):
        distance = int((word ^ inspector_cls._bch_format(payload)).bit_count())
        result.append({
            "distance": distance,
            "mask": payload & 7,
            "ec": {0: "M", 1: "L", 2: "H", 3: "Q"}[payload >> 3],
        })
    return sorted(result, key=lambda item: (item["distance"], item["mask"]))[:2]


def _alignment_checks(rows: tuple[str, ...], inspector_cls: Any) -> list[dict[str, int]]:
    n = len(rows)
    version = (n - 17) // 4
    positions = inspector_cls._alignment_positions(version, n)
    records: list[dict[str, int]] = []
    for cy in positions:
        for cx in positions:
            if (cy == 6 and cx in (6, n - 7)) or (cx == 6 and cy == n - 7):
                continue
            hits = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    expected = "1" if max(abs(dx), abs(dy)) in (0, 2) else "0"
                    hits += rows[cy + dy][cx + dx] == expected
            records.append({"x": cx, "y": cy, "matches": int(hits), "total": 25})
    return records


def _decode_zxing(rows: tuple[str, ...]) -> dict[str, Any]:
    """Usa a mesma biblioteca de leitura do BarcodeReader, em memória."""
    try:
        import zxingcpp
        from PIL import Image
    except ImportError as exc:
        return {"status": "DEPENDENCIA_INDISPONIVEL", "module": exc.name}

    n = len(rows)
    base = n + 8  # quiet zone de 4 módulos por lado
    pixels = bytearray([255]) * (base * base)
    for y, line in enumerate(rows):
        for x, bit in enumerate(line):
            if bit == "1":
                pixels[(y + 4) * base + (x + 4)] = 0
    image = Image.frombytes("L", (base, base), bytes(pixels)).convert("RGB")
    nearest = getattr(getattr(Image, "Resampling", Image), "NEAREST")

    for scale in (4, 8, 12):
        scaled = image.resize((base * scale, base * scale), resample=nearest)
        try:
            detections = zxingcpp.read_barcodes(scaled)
        except Exception as exc:
            return {"status": "ERRO_LEITOR", "error_type": type(exc).__name__}
        for detected in detections:
            fmt = str(getattr(detected, "format", "")).casefold()
            if "qr" not in fmt:
                continue
            text = getattr(detected, "text", "")
            if not isinstance(text, str) or not text:
                continue
            return {
                "status": "PAYLOAD_DECODIFICADO",
                "text": text,  # em memória; NUNCA será impresso
                "length": len(text.encode("utf-8", errors="replace")),
                "sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
                "scale": scale,
            }
    return {"status": "SEM_DECODIFICACAO"}


def _compare_existing_qr(path: Any, page_number: int, decoded_text: str) -> dict[str, Any]:
    """Vincula somente leituras QR na MESMA página, com igualdade textual exata."""
    from app.domain.readers.barcode_reader import BarcodeReader

    try:
        barcodes = BarcodeReader().read(str(path))
    except Exception as exc:
        return {"status": "LEITURA_VISUAL_INDISPONIVEL", "error_type": type(exc).__name__}
    qr_values = []
    for barcode in barcodes:
        fmt = str(getattr(barcode, "format", "") or "").casefold()
        if "qr" not in fmt or getattr(barcode, "page_number", None) != page_number:
            continue
        content = getattr(barcode, "content", None)
        if isinstance(content, str):
            qr_values.append(content)

    return {
        "status": "COMPARACAO_REALIZADA" if qr_values else "SEM_QR_VISUAL_COM_PAYLOAD_NA_PAGINA",
        "visual_qrs": len(qr_values),
        "matching_qrs": sum(content == decoded_text for content in qr_values),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sha")
    source.add_argument("--pdf")
    args = parser.parse_args()

    try:
        import pymupdf
        from diagnostico_cfqa0039_5_padroes import locate, analyze_rows
        from diagnostico_cfqa0039_5_margens_qr import probe, _rows_from_group
        from diagnostico_cfqa0039_5_nucleo_qr import _restore_core
        from app.domain.services.qr_matrix_inspector import QrMatrixInspector
        from app.domain.services.qr_structural_inspector import QrStructuralInspector

        path = locate(args.pdf, args.sha)
        structural = QrStructuralInspector()
        print("=" * 72)
        print("DocDNA | CF-QA 003.9.5 — formato independente e ZXing")
        print("Somente leitura | não imprime matrizes nem payloads")
        print("PDF:", path.name)
        groups_count = 0
        with pymupdf.open(str(path)) as doc:
            for page_number, page in enumerate(doc, 1):
                if page_number > structural.MAX_PAGES:
                    break
                groups = structural._group(structural._candidate_spans(page, page_number))
                for group in groups[:structural.MAX_GROUPS_PER_PAGE]:
                    groups_count += 1
                    print("-" * 72)
                    print(f"Grupo {groups_count} | Página {page_number} | Fonte {group.get('font_name')}")
                    if group.get("truncated"):
                        print("Inconclusivo: captura truncada")
                        continue
                    rows = _rows_from_group(group)
                    if rows is None:
                        print("Inconclusivo: sequência não permite grade quadrada")
                        continue
                    outcome = probe(rows)
                    best = outcome.get("valid") or outcome.get("best")
                    if not best:
                        print("Inconclusivo: sem candidato de núcleo")
                        continue
                    core = _restore_core(rows, best)
                    if core is None:
                        print("Inconclusivo: orientação ou recorte não recuperado")
                        continue
                    report = analyze_rows(core)
                    a, b = _read_format_copies(core)
                    ca = _format_candidates(a, QrMatrixInspector)
                    cb = _format_candidates(b, QrMatrixInspector)
                    align = _alignment_checks(core, QrMatrixInspector)
                    print("Matriz externa:", f"{len(rows)}x{len(rows)}")
                    print("Núcleo:", f"{len(core)}x{len(core)}", "| versão", best["version"])
                    print("Margens (E,S,D,I):",
                          best["x_offset"], best["y_offset"],
                          best["right_margin"], best["bottom_margin"])
                    print("Margem clara:", f"{best['margin_light_ratio']:.1%}")
                    print("Localizadores:", f"{report['finder_match']}/147",
                          "| separadores:", f"{report['separator_match']}/{report['separator_total']}",
                          "| sincronização:", f"{report['timing_match']}/{report['timing_total']}")
                    print("Alinhamento por centro (x,y => acertos/25):")
                    for item in align:
                        print(f"  ({item['x']},{item['y']}) => {item['matches']}/25")
                    print("Módulo escuro fixo:", report["dark_module_expected"])
                    print("Cópias REAIS do formato: diferenças entre elas:", (a ^ b).bit_count(), "bit(s)")
                    for name, candidates in (("superior-esquerda", ca), ("direita/inferior", cb)):
                        print(f"  {name}: distância BCH mínima = {candidates[0]['distance']};",
                              f"máscara candidata = {candidates[0]['mask']};",
                              f"nível EC candidato = {candidates[0]['ec']}")
                    print("Cópias de versão coerentes:", report["version_bits_match"])
                    print("Validação estrita:", report["fully_validated"])
                    decoded = _decode_zxing(core)
                    print("ZXing na matriz reconstruída:", decoded["status"])
                    if decoded["status"] == "PAYLOAD_DECODIFICADO":
                        print("  Tamanho (bytes):", decoded["length"],
                              "| SHA-256:", decoded["sha256"])
                        compared = _compare_existing_qr(path, page_number, decoded["text"])
                        print("  Comparação com QR visual existente:", compared["status"])
                        if "visual_qrs" in compared:
                            print("  QR(s) visuais na página:", compared["visual_qrs"],
                                  "| conteúdo idêntico:", compared["matching_qrs"])
                    print("Classificação do DocDNA: INALTERADA")
        print("=" * 72)
        print("Grupos examinados:", groups_count)
        print("A decodificação não comprova ocultação, autenticidade ou fraude.")
        return 0
    except Exception as exc:
        print("Diagnóstico interrompido:", type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
