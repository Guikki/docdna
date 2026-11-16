"""DocDNA CF-QA 003.9.5 — diagnóstico do núcleo QR após remover margens.

Leitura exclusivamente diagnóstica. Não altera arquivo, código de produção,
classificação de ocultação, Prompt Injection ou resultados persistidos.
Não imprime sequências binárias nem payload do QR (somente hash, se decodificado).

Na raiz do DocDNA:
    python diagnostico_cfqa0039_5_nucleo_qr.py --sha 7bb5e20cb9f857fa38071d164bc3ffdc85e72b0d0db87be9e75763757c46c9d5
    python diagnostico_cfqa0039_5_nucleo_qr.py --pdf "caminho/arquivo.pdf"

Dependências do projeto: pymupdf, qr_matrix_inspector; cv2 é opcional.
Requer os diagnósticos anteriores de padrões e margens na mesma pasta.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from typing import Any

from diagnostico_cfqa0039_5_margens_qr import _rows_from_group, probe
from diagnostico_cfqa0039_5_padroes import analyze_rows, locate
from app.domain.services.qr_matrix_inspector import QrMatrixInspector
from app.domain.services.qr_structural_inspector import QrStructuralInspector


def _restore_core(rows: tuple[str, ...], best: dict[str, Any]) -> tuple[str, ...] | None:
    """Reaplica EXATAMENTE o recorte vencedor, sem procurar outra matriz."""
    n = int(best["dimension"])
    x0 = int(best["x_offset"])
    y0 = int(best["y_offset"])
    for label, inverted, transformed in QrMatrixInspector._orientations(rows):
        if label == best["orientation"] and inverted == best["inverted"]:
            return tuple(transformed[y][x0:x0 + n] for y in range(y0, y0 + n))
    return None


def _closest_format(value: int) -> dict[str, int]:
    matches = []
    for payload in range(32):
        valid_word = QrMatrixInspector._bch_format(payload)
        matches.append((int((value ^ valid_word).bit_count()), payload))
    distance, data = min(matches)
    return {"bit_errors": distance, "format_data": data,
            "mask_pattern": data & 7, "ec_code": data >> 3}


def _version_mismatches(rows: tuple[str, ...]) -> tuple[int, int] | None:
    n = len(rows)
    version = (n - 17) // 4
    if version < 7:
        return None
    word = QrMatrixInspector._bch_version(version)
    first = second = 0
    for i in range(18):
        expected = str((word >> i) & 1)
        first += rows[i // 3][n - 11 + i % 3] != expected
        second += rows[n - 11 + i % 3][i // 3] != expected
    return int(first), int(second)


def analyze_core(rows: tuple[str, ...]) -> dict[str, Any]:
    report = analyze_rows(rows)
    fa = QrMatrixInspector._format_value(rows, vertical=True)
    fb = QrMatrixInspector._format_value(rows, vertical=False)
    return {
        "report": report,
        "format_copy_a": _closest_format(fa),
        "format_copy_b": _closest_format(fb),
        "format_copy_distance": int((fa ^ fb).bit_count()),
        "version_copy_errors": _version_mismatches(rows),
    }


def _decode_locally(rows: tuple[str, ...]) -> dict[str, Any]:
    """Decodificação opcional em memória, nunca executa nem imprime payload."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"status": "DEPENDENCIA_INDISPONIVEL"}
    n = len(rows)
    # Inclui zona de silêncio padrão no raster criado a partir dos módulos.
    canvas = np.full((n + 8, n + 8), 255, dtype=np.uint8)
    for y, line in enumerate(rows):
        for x, bit in enumerate(line):
            if bit == "1":
                canvas[y + 4, x + 4] = 0
    detector = cv2.QRCodeDetector()
    for scale in (6, 10):
        pixels = cv2.resize(canvas, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_NEAREST)
        try:
            payload, points, _ = detector.detectAndDecode(pixels)
        except cv2.error:
            continue
        if payload:
            raw = payload.encode("utf-8", errors="replace")
            return {"status": "PAYLOAD_DECODIFICADO",
                    "length": len(raw), "sha256": sha256(raw).hexdigest()}
    return {"status": "SEM_DECODIFICACAO"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sha")
    source.add_argument("--pdf")
    args = parser.parse_args()
    try:
        import pymupdf
        path = locate(args.pdf, args.sha)
        structural = QrStructuralInspector()
        print("=" * 72)
        print("DocDNA | CF-QA 003.9.5 — checagem dos 57x57 modulos internos")
        print("Somente leitura | nao imprime bits nem conteudo do QR")
        print("PDF:", path.name)
        count = 0
        with pymupdf.open(str(path)) as document:
            for page_number, page in enumerate(document, start=1):
                if page_number > structural.MAX_PAGES:
                    break
                groups = structural._group(structural._candidate_spans(page, page_number))
                for group in groups[:structural.MAX_GROUPS_PER_PAGE]:
                    count += 1
                    print("-" * 72)
                    print(f"Grupo {count} | pagina {page_number} | fonte {group.get('font_name')}")
                    if group.get("truncated"):
                        print("INCONCLUSIVO: grupo truncado")
                        continue
                    rows = _rows_from_group(group)
                    if rows is None:
                        print("INCONCLUSIVO: sequencia binaria nao permite grade quadrada")
                        continue
                    scan = probe(rows)
                    best = scan.get("valid") or scan.get("best")
                    if not best:
                        print("INCONCLUSIVO: nenhum nucleo candidato")
                        continue
                    core = _restore_core(rows, best)
                    if core is None:
                        print("INCONCLUSIVO: falha na reconstrução da orientacao")
                        continue
                    data = analyze_core(core)
                    rep = data["report"]
                    print(f"Grade externa: {len(rows)}x{len(rows)}")
                    print(f"Nucleo candidato: {len(core)}x{len(core)} | versao {best['version']}")
                    print("Margens (esq, sup, dir, inf):",
                          f"{best['x_offset']}, {best['y_offset']},",
                          f"{best['right_margin']}, {best['bottom_margin']}")
                    print(f"Margem clara: {best['margin_light_ratio']:.1%}")
                    print(f"Orientacao: {best['orientation']} | invertida: {best['inverted']}")
                    print(f"Localizadores: {rep['finder_match']}/147")
                    print(f"Separadores: {rep['separator_match']}/{rep['separator_total']}")
                    print(f"Sincronizacao: {rep['timing_match']}/{rep['timing_total']}")
                    print(f"Alinhamento: {rep['alignment_match']}/{rep['alignment_total']}")
                    print("Modulo escuro fixo:", rep["dark_module_expected"])
                    print("Formato: copias iguais:", rep["format_copies_equal"],
                          "| ambas BCH validas:", rep["format_bch_valid"])
                    print("Diferenca entre copias de formato:",
                          data["format_copy_distance"], "bit(s)")
                    for label in ("format_copy_a", "format_copy_b"):
                        fmt = data[label]
                        print(f"  {label}: menor distancia BCH = {fmt['bit_errors']} bit(s);",
                              "padrao de mascara candidato =", fmt["mask_pattern"],
                              "(apenas diagnostico)")
                    if data["version_copy_errors"] is not None:
                        print("Divergencias dos 18 bits de versao (copia A, B):",
                              *data["version_copy_errors"])
                    print("Verificador completo:", rep["fully_validated"])
                    decoded = _decode_locally(core)
                    print("Decodificador independente OpenCV:", decoded["status"])
                    if decoded["status"] == "PAYLOAD_DECODIFICADO":
                        print("Payload decodificado: bytes =", decoded["length"],
                              "| SHA-256 =", decoded["sha256"])
                    print("Conclusao: nenhuma classificacao ou alerta foi alterado")
        print("=" * 72)
        print("Grupos examinados:", count)
        return 0
    except Exception as exc:
        print(f"Diagnostico interrompido: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
