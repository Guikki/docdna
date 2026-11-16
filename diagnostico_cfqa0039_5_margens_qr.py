"""CF-QA 003.9.5 — diagnostico conservador de margens em matrizes QR.

Executar da raiz do DocDNA, apos os diagnosticos anteriores:
    python diagnostico_cfqa0039_5_margens_qr.py --sha <sha256>
    python diagnostico_cfqa0039_5_margens_qr.py --pdf "caminho/arquivo.pdf"

Nao modifica arquivos nem classificacoes; nao mostra bits ou payloads;
nao conclui ocultacao, fraude ou Prompt Injection.

Investiga se uma matriz extraida com N x N bits inclui bordas/margens,
como QR de 57x57 com quatro modulos de margem de cada lado (N=65).
"""
from __future__ import annotations

import argparse
from typing import Any

from diagnostico_cfqa0039_5_padroes import locate
from app.domain.services.qr_matrix_inspector import QrMatrixInspector
from app.domain.services.qr_structural_inspector import QrStructuralInspector


# Apenas recortes moderados: nao tenta produzir QR a partir de partes arbitrarias.
MAX_BORDER_PER_AXIS = 12


def _finder_matches(rows: tuple[str, ...]) -> int:
    """Acertos nos 147 modulos dos tres localizadores (nao valida QR)."""
    n = len(rows)
    count = 0
    for x0, y0 in ((0, 0), (n - 7, 0), (0, n - 7)):
        for dy in range(7):
            for dx in range(7):
                expected = "1" if (
                    dx in (0, 6) or dy in (0, 6)
                    or (2 <= dx <= 4 and 2 <= dy <= 4)
                ) else "0"
                count += rows[y0 + dy][x0 + dx] == expected
    return count


def _margin_light_ratio(rows: tuple[str, ...], x0: int, y0: int, size: int) -> float:
    n = len(rows)
    white = total = 0
    for y in range(n):
        for x in range(n):
            if x0 <= x < x0 + size and y0 <= y < y0 + size:
                continue
            total += 1
            white += rows[y][x] == "0"
    return white / total if total else 1.0


def probe(rows: tuple[str, ...], *, max_border: int = MAX_BORDER_PER_AXIS) -> dict[str, Any]:
    """Busca QR estruturalmente valido inteiramente contido na grade extraida.

    Nao assume que remover uma margem transforma qualquer sequencia em QR.
    So retorna confirmacao se o verificador existente aprovar a matriz interna.
    """
    n = len(rows)
    inspector = QrMatrixInspector
    if n < 21 or any(len(row) != n or set(row) - {"0", "1"} for row in rows):
        return {"reason": "grade binaria quadrada indisponivel", "valid": None, "best": None,
                "tested": 0}
    if n > inspector.MAX_SIZE:
        return {"reason": "dimensao acima do limite", "valid": None, "best": None,
                "tested": 0}

    tested = 0
    best = None
    # Sem recorte, depois regioes cujo deslocamento total por eixo e moderado.
    sizes = [size for size in range(n, 20, -1)
             if (size - 17) % 4 == 0 and n - size <= max_border]
    for orientation, inverted, candidate in inspector._orientations(rows):
        for size in sizes:
            slack = n - size
            for y0 in range(slack + 1):
                for x0 in range(slack + 1):
                    if slack == 0:
                        core = candidate
                    else:
                        core = tuple(candidate[y][x0:x0 + size]
                                     for y in range(y0, y0 + size))
                    tested += 1
                    hits = _finder_matches(core)
                    margin_ratio = _margin_light_ratio(candidate, x0, y0, size)
                    entry = {"dimension": size, "version": (size - 17) // 4,
                             "x_offset": x0, "y_offset": y0,
                             "right_margin": n - (x0 + size),
                             "bottom_margin": n - (y0 + size),
                             "orientation": orientation, "inverted": inverted,
                             "finder_hits": hits, "margin_light_ratio": margin_ratio}
                    if best is None or (hits, margin_ratio) > (best["finder_hits"], best["margin_light_ratio"]):
                        best = entry
                    # O verificador completo so e tentado se os localizadores
                    # estiverem perfeitos: qualquer QR estruturalmente valido
                    # precisa passar por esta condicao.
                    if hits == 147 and inspector._validate(core) is not None:
                        return {"reason": "padroes estruturais do QR validados", "valid": entry,
                                "best": best, "tested": tested}
    return {"reason": "nenhum recorte moderado validou a estrutura QR",
            "valid": None, "best": best, "tested": tested}


def _rows_from_group(group: dict[str, Any]) -> tuple[str, ...] | None:
    fragments = group.get("texts", ())
    if not isinstance(fragments, (list, tuple)):
        return None
    if not all(isinstance(item, str) for item in fragments):
        return None
    cleaned = ["".join(item.split()) for item in fragments]
    if any(set(item) - {"0", "1"} for item in cleaned):
        return None
    joined = "".join(cleaned)
    from math import isqrt
    n = isqrt(len(joined))
    if n * n != len(joined) or not 21 <= n <= 177:
        return None
    return tuple(joined[i:i + n] for i in range(0, len(joined), n))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    arg = parser.add_mutually_exclusive_group(required=True)
    arg.add_argument("--sha")
    arg.add_argument("--pdf")
    args = parser.parse_args()
    try:
        import pymupdf
        path = locate(args.pdf, args.sha)
        structural = QrStructuralInspector()
        count = 0
        print("=" * 72)
        print("DocDNA | CF-QA 003.9.5 — margens e recortes de matriz QR")
        print("Somente leitura | sem alteracoes de classificacao ou conteudo")
        print("PDF:", path.name)
        with pymupdf.open(str(path)) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                if page_number > structural.MAX_PAGES:
                    break
                groups = structural._group(structural._candidate_spans(page, page_number))
                for group in groups[:structural.MAX_GROUPS_PER_PAGE]:
                    count += 1
                    print("-" * 72)
                    print(f"Grupo {count} | Pagina {page_number} | Fonte: {group.get('font_name')}")
                    if group.get("truncated"):
                        print("Resultado: INCONCLUSIVO — grupo truncado")
                        continue
                    rows = _rows_from_group(group)
                    if rows is None:
                        print("Resultado: INCONCLUSIVO — grade binaria indisponivel")
                        continue
                    print(f"Grade extraida: {len(rows)} x {len(rows)}")
                    outcome = probe(rows)
                    print("Recortes examinados:", outcome["tested"])
                    if outcome["valid"] is not None:
                        record = outcome["valid"]
                        print("Resultado: QR_INTERNO_ESTRUTURALMENTE_VALIDADO")
                        print(f"Matriz interna: {record['dimension']} x {record['dimension']} | Versao: {record['version']}")
                        print(f"Margens (esq, sup, dir, inf): "
                              f"{record['x_offset']}, {record['y_offset']}, "
                              f"{record['right_margin']}, {record['bottom_margin']}")
                        print(f"Orientacao: {record['orientation']} | Invertida: {record['inverted']}")
                        print(f"Margem clara (proporcao): {record['margin_light_ratio']:.1%}")
                        print("Observacao: validacao estrutural NAO e comparacao de payload.")
                    else:
                        print("Resultado: QR_MATRIX_CANDIDATE_UNCONFIRMED")
                        best = outcome["best"]
                        if best:
                            print(f"Maior correspondencia de localizadores: {best['finder_hits']}/147")
                            print(f"Dimensao candidata: {best['dimension']} | Versao: {best['version']}")
                            print(f"Margens candidatas (esq, sup, dir, inf): "
                                  f"{best['x_offset']}, {best['y_offset']}, "
                                  f"{best['right_margin']}, {best['bottom_margin']}")
                            print(f"Orientacao: {best['orientation']} | Invertida: {best['inverted']}")
                            print(f"Proporcao de margem clara: {best['margin_light_ratio']:.1%}")
                        print("Proxima hipotese: mapeamento dos glifos da fonte PDF ou outra representacao.")
        print("=" * 72)
        print("Grupos examinados:", count)
        print("Nenhum resultado confirma ocultacao visual, fraude ou Prompt Injection.")
        return 0
    except Exception as exc:
        print(f"Diagnostico interrompido: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
