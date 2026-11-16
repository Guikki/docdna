"""CF-QA 003.9.5 — diagnóstico das estruturas da matriz (somente leitura).

Execução na raiz do DocDNA:
    python diagnostico_cfqa0039_5_padroes.py --sha <sha256>
    python diagnostico_cfqa0039_5_padroes.py --pdf "caminho/arquivo.pdf"

Não altera produção, não grava dados, não executa payloads, não exporta bits
brutos e não conclui ocultação, fraude, igualdade de QR ou Prompt Injection.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any


def locate(path: str | None, sha: str | None) -> Path:
    if path:
        candidate = Path(path).expanduser().resolve()
        if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
            raise ValueError("PDF não encontrado")
        return candidate
    expected = (sha or "").strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("SHA-256 inválido")
    for candidate in Path("storage/uploads").glob("*.pdf"):
        digest = hashlib.sha256()
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() == expected:
            return candidate.resolve()
    raise FileNotFoundError("PDF não localizado em storage/uploads")


def analyze_rows(rows: tuple[str, ...]) -> dict[str, Any]:
    """Conta correspondências com padrões fixos; não confirma um QR."""
    n = len(rows)
    if not n or any(len(row) != n or set(row) - {"0", "1"} for row in rows):
        raise ValueError("Matriz binária quadrada inválida")
    if (n - 17) % 4 or not 21 <= n <= 177:
        raise ValueError("Dimensão não pertence ao QR convencional")
    version = (n - 17) // 4
    finders = {}
    for label, x0, y0 in (
        ("superior_esquerdo", 0, 0),
        ("superior_direito", n - 7, 0),
        ("inferior_esquerdo", 0, n - 7),
    ):
        count = 0
        for dy in range(7):
            for dx in range(7):
                expected = "1" if (
                    dx in (0, 6) or dy in (0, 6)
                    or (2 <= dx <= 4 and 2 <= dy <= 4)
                ) else "0"
                count += rows[y0 + dy][x0 + dx] == expected
        finders[label] = int(count)

    separators: set[tuple[int, int]] = set()
    for yy in range(8):
        separators.add((7, yy))
        separators.add((n - 8, yy))
    for xx in range(8):
        separators.add((xx, 7))
        separators.add((xx, n - 8))
    for xx in range(n - 8, n):
        separators.add((xx, 7))
    for yy in range(n - 8, n):
        separators.add((7, yy))
    separator_match = sum(rows[y][x] == "0" for x, y in separators)

    timing_total = 2 * (n - 16)
    # Avaliar as duas linhas de sincronização independentemente.
    timing_match = 0
    for i in range(8, n - 8):
        expected = "1" if i % 2 == 0 else "0"
        timing_match += rows[6][i] == expected
        timing_match += rows[i][6] == expected

    from app.domain.services.qr_matrix_inspector import QrMatrixInspector
    inspector = QrMatrixInspector
    align_positions = inspector._alignment_positions(version, n)
    alignment_total = 0
    alignment_match = 0
    for cy in align_positions:
        for cx in align_positions:
            if (cy == 6 and cx in (6, n - 7)) or (cx == 6 and cy == n - 7):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    expected = "1" if max(abs(dx), abs(dy)) in (0, 2) else "0"
                    alignment_total += 1
                    alignment_match += rows[cy + dy][cx + dx] == expected

    fmt_a = inspector._format_value(rows, vertical=True)
    fmt_b = inspector._format_value(rows, vertical=False)
    valid_formats = {inspector._bch_format(i) for i in range(32)}
    format_equal = fmt_a == fmt_b
    format_bch = fmt_a in valid_formats and fmt_b in valid_formats
    version_bits_match = None
    if version >= 7:
        expected_version = inspector._bch_version(version)
        version_bits_match = all(
            rows[i // 3][n - 11 + i % 3] == str((expected_version >> i) & 1)
            and rows[n - 11 + i % 3][i // 3] == str((expected_version >> i) & 1)
            for i in range(18)
        )
    return {
        "finders": finders,
        "finder_match": sum(finders.values()),
        "separator_match": int(separator_match),
        "separator_total": len(separators),
        "timing_match": int(timing_match),
        "timing_total": timing_total,
        "alignment_match": int(alignment_match),
        "alignment_total": alignment_total,
        "format_copies_equal": format_equal,
        "format_bch_valid": format_bch,
        "version_bits_match": version_bits_match,
        "dark_module_expected": rows[n - 8][8] == "1",
        "fully_validated": inspector._validate(rows) is not None,
    }


def inspect_group(group: dict[str, Any]) -> dict[str, Any]:
    from app.domain.services.qr_matrix_inspector import QrMatrixInspector
    inspector = QrMatrixInspector()
    finding = inspector.inspect_group(group)
    outcome: dict[str, Any] = {"finding": finding, "best": None}
    n = finding.get("dimension")
    if type(n) is not int:
        return outcome
    fragments = group.get("texts", ())
    if not isinstance(fragments, (tuple, list)) or not all(isinstance(t, str) for t in fragments):
        return outcome
    bits = "".join("".join(fragment.split()) for fragment in fragments)
    if len(bits) != n * n or set(bits) - {"0", "1"}:
        return outcome
    rows = tuple(bits[i:i+n] for i in range(0, len(bits), n))
    for orientation, inverted, candidate in inspector._orientations(rows):
        report = analyze_rows(candidate)
        score = (
            report["finder_match"], report["separator_match"],
            report["timing_match"], report["alignment_match"],
        )
        if outcome["best"] is None or score > outcome["best"]["score"]:
            outcome["best"] = {
                "orientation": orientation,
                "inverted": inverted,
                "score": score,
                "report": report,
            }
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha")
    target.add_argument("--pdf")
    args = parser.parse_args()
    try:
        import pymupdf
        from app.domain.services.qr_structural_inspector import QrStructuralInspector
        path = locate(args.pdf, args.sha)
        structural = QrStructuralInspector()
        count = 0
        print("=" * 72)
        print("DOCDNA | CF-QA 003.9.5 — diagnóstico de padrões QR")
        print("Somente leitura; não imprime bits nem conteúdo dos QR Codes")
        print("PDF:", path.name)
        with pymupdf.open(str(path)) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                if page_number > structural.MAX_PAGES:
                    break
                spans = structural._candidate_spans(page, page_number)
                groups = structural._group(spans)
                for group in groups[:structural.MAX_GROUPS_PER_PAGE]:
                    count += 1
                    result = inspect_group(group)
                    finding = result["finding"]
                    print("-" * 72)
                    print(f"Grupo {count} | Página {page_number} | Fonte {group.get('font_name')}")
                    print(f"Fragmentos: {finding.get('fragment_count')} | Bits: {finding.get('bit_count')}")
                    print(f"Dimensão: {finding.get('dimension')} | Versão: {finding.get('version')}")
                    print(f"Status: {finding.get('status')}")
                    best = result["best"]
                    if best is None:
                        print("Sem matriz quadrada binária adequada para comparação")
                        continue
                    r = best["report"]
                    print(f"Melhor orientação: {best['orientation']} | Invertida: {best['inverted']}")
                    print("Localizadores (acertos de 49):", ", ".join(
                        f"{key}={value}/49" for key, value in r["finders"].items()))
                    print(f"Total de localizadores: {r['finder_match']}/147")
                    print(f"Separadores: {r['separator_match']}/{r['separator_total']}")
                    print(f"Sincronização: {r['timing_match']}/{r['timing_total']}")
                    print(f"Alinhamento: {r['alignment_match']}/{r['alignment_total']}")
                    print(f"Formato: cópias iguais={r['format_copies_equal']} | BCH válido={r['format_bch_valid']}")
                    print(f"Versão codificada consistente: {r['version_bits_match']}")
                    print(f"Módulo escuro fixo: {r['dark_module_expected']}")
                    print(f"Validador completo: {r['fully_validated']}")
        print("=" * 72)
        print("Grupos examinados:", count)
        print("Os escores não demonstram identidade de payload nem ocultação visual.")
        return 0
    except Exception as exc:
        print(f"Diagnóstico interrompido: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
