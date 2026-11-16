"""DocDNA CF-QA 003.7.1 — auditoria espacial do OCR (somente leitura).

Objetivo: distinguir três problemas sem alterar o DocDNA:
1) token não foi reconhecido pelo Tesseract;
2) token foi lido, mas com rótulo degradado;
3) token e rótulo foram lidos, porém distantes geometricamente.

Instalação: copiar este arquivo para a raiz do projeto DocDNA.
Exemplo:
 python diagnostico_cfqa0037_1_geometria_ocr.py --sha <sha256-do-pdf>
 python diagnostico_cfqa0037_1_geometria_ocr.py --pdf "C:\\documentos\\fatura.pdf"

Não escreve arquivos, não cria análises e não consulta serviços externos.
A saída pode conter dados cadastrais: compartilhe apenas se apropriado.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re
import unicodedata

from app.config.settings import settings
from app.domain.readers.ocr_reader import OcrReader

MONEY = re.compile(r"(?<!\d)(?:\d{1,3}(?:\.\d{3})+|\d+)[,.]\d{2}(?!\d)")
LONG_NUMBER = re.compile(r"(?<!\d)\d[\d.\-/ ]{5,28}\d(?!\d)")
ANCHOR = re.compile(r"total|pagar|valor|venc|fatur|debito|automatic|titular|cliente|conta|codig|nome", re.I)
MAX_NEIGHBORS = 18


def _read_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _norm(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _resolve(pdf, digest):
    if pdf:
        target = Path(pdf).expanduser().resolve()
        if not target.is_file() or target.suffix.lower() != ".pdf":
            raise FileNotFoundError(f"PDF não encontrado: {target}")
        return target
    if not digest or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        raise ValueError("Informe --pdf ou --sha (64 dígitos hexadecimais).")
    root = Path(settings.UPLOADS_DIR)
    if not root.is_dir():
        raise FileNotFoundError(f"Diretório de uploads inexistente: {root}")
    for candidate in root.rglob("*.pdf"):
        h = sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() == digest.lower():
            return candidate
    raise FileNotFoundError("SHA não encontrado em UPLOADS_DIR")


def _boxes(raw):
    clean = []
    for idx, box in enumerate(raw, start=1):
        page = _read_field(box, "page_number")
        text = str(_read_field(box, "text", "") or "").strip()
        coords = [_read_field(box, key) for key in ("left", "top", "width", "height")]
        if type(page) is not int or page < 1 or not text:
            continue
        try:
            x, y, w, h = [float(v) for v in coords]
        except (TypeError, ValueError, OverflowError):
            continue
        if not all(isfinite(z) for z in (x, y, w, h)) or w <= 0 or h <= 0:
            continue
        confidence = _read_field(box, "confidence")
        try:
            confidence = float(confidence)
            if not isfinite(confidence):
                confidence = None
        except (ValueError, TypeError):
            confidence = None
        clean.append({"id": idx, "page": page, "text": text, "x": x, "y": y,
                      "w": w, "h": h, "conf": confidence})
    return clean


def _fmt(b):
    conf = "?" if b["conf"] is None else f'{b["conf"]:.0f}'
    return (f'P{b["page"]} x={b["x"]:.0f} y={b["y"]:.0f} '
            f'w={b["w"]:.0f} h={b["h"]:.0f} c={conf:>3}  {b["text"]!r}')


def _visual_row(candidate, page_boxes, *, vertical=13, horizontal=900):
    cy = candidate["y"] + candidate["h"] / 2
    row = [b for b in page_boxes if b["id"] != candidate["id"]
           and abs((b["y"] + b["h"] / 2) - cy) <= vertical
           and abs(b["x"] - candidate["x"]) <= horizontal]
    row.append(candidate)
    row.sort(key=lambda b: b["x"])
    return " ".join(b["text"] for b in row)[:280]


def _nearby(target, page_boxes, *, dx=360, dy_above=65, dy_below=105):
    center = target["x"] + target["w"] / 2
    near = [b for b in page_boxes if b["id"] != target["id"]
            and -dy_above <= b["y"] - target["y"] <= dy_below
            and abs((b["x"] + b["w"] / 2) - center) <= dx]
    near.sort(key=lambda b: (abs(b["y"] - target["y"]),
                             abs(b["x"] - target["x"])))
    return sorted(near[:MAX_NEIGHBORS], key=lambda b: (b["y"], b["x"]))


def inspect(boxes, *, max_anchors=22, max_numbers=50):
    """Gera uma auditoria legível para a saída de OCR, sem calcular achados."""
    pages = defaultdict(list)
    for box in boxes:
        pages[box["page"]].append(box)
    for page_number in sorted(pages):
        words = pages[page_number]
        anchors = [b for b in words if ANCHOR.search(_norm(b["text"]))]
        prices = [b for b in words if MONEY.search(b["text"])]
        numerics = [b for b in words if len(re.sub(r"\D", "", b["text"])) >= 7
                    and LONG_NUMBER.search(b["text"])]
        print(f'\n=== PÁGINA {page_number} | palavras={len(words)} '
              f'| âncoras={len(anchors)} | valores monetários={len(prices)} '
              f'| números longos={len(numerics)} ===')
        print('\n--- VALORES MONETÁRIOS RECONHECIDOS PELO OCR ---')
        if not prices:
            print('Nenhum valor monetário reconhecido como um token. OCR pode ter fragmentado os números.')
        for b in prices[:max_numbers]:
            print(_fmt(b))
            print('  Linha aproximada:', _visual_row(b, words))
            same_region = [a for a in anchors if abs(a["y"] - b["y"]) <= 110]
            same_region.sort(key=lambda a: (abs(a["y"]-b["y"]), abs(a["x"]-b["x"])))
            print('  Âncoras próximas:', ', '.join(
                f'{a["text"]!r}@({a["x"]:.0f},{a["y"]:.0f})' for a in same_region[:6]
            ) or '[nenhuma a até 110 px de distância vertical]')
        if len(prices) > max_numbers:
            print(f'[mais {len(prices)-max_numbers} valores omitidos pelo limite]')
        print('\n--- NÚMEROS LONGOS RECONHECIDOS ---')
        if not numerics:
            print('Nenhum token numérico longo reconhecido.')
        for b in numerics[:max_numbers]:
            print(_fmt(b))
        if len(numerics) > max_numbers:
            print(f'[mais {len(numerics)-max_numbers} tokens numéricos omitidos]')
        print('\n--- RÓTULOS E VIZINHANÇA REAL ---')
        if not anchors:
            print('Nenhum dos rótulos esperados foi lido claramente.')
        # Mostrar âncoras distribuídas na página e priorizar explicitamente
        # totais/faturas/debito antes de palavras comuns ("conta").
        importance = lambda b: (
            0 if re.search('total|pagar|fatur|debito|automatic|titular', _norm(b['text']))
            else 1, b['y'], b['x']
        )
        for a in sorted(anchors, key=importance)[:max_anchors]:
            print('\nÂNCORA', _fmt(a))
            print('  Linha aproximada:', _visual_row(a, words))
            for neighbor in _nearby(a, words):
                print('   ', _fmt(neighbor))
        if len(anchors) > max_anchors:
            print(f'[{len(anchors)-max_anchors} âncoras omitidas]')
        print('\n--- TOKENS OCR DEGRADADOS QUE PODEM SER RÓTULOS ---')
        suspicious = [b for b in words if re.search(
            r'nida|nida|totala|debit|contal|pagar-|fatura|\bnda\b', _norm(b['text']))]
        for b in suspicious[:25]:
            print(_fmt(b))
            print('  Linha aproximada:', _visual_row(b, words))


def main():
    parser = argparse.ArgumentParser(description='Diagnóstico espacial de OCR do DocDNA, somente leitura')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sha', help='SHA-256 do PDF no storage/uploads')
    group.add_argument('--pdf', help='Caminho do PDF')
    parser.add_argument('--max-anchors', type=int, default=22,
                        help='Máximo de âncoras por página (padrão: 22)')
    parser.add_argument('--max-numbers', type=int, default=50,
                        help='Máximo de valores/identificadores por página (padrão: 50)')
    args = parser.parse_args()
    target = _resolve(args.pdf, args.sha)
    print('DOCDNA — CF-QA 003.7.1 | AUDITORIA ESPACIAL OCR — SOMENTE LEITURA')
    print('PDF:', target)
    result = OcrReader().read(str(target))
    words = _boxes(list(result.text_boxes))
    print('Caixas OCR totais:', len(result.text_boxes), '| utilizáveis:', len(words))
    print('Observação: são coordenadas da imagem OCR, não pontos PDF.')
    print('Os trechos de OCR podem conter dados pessoais. Revise antes de compartilhar.')
    inspect(words, max_anchors=max(0, args.max_anchors),
            max_numbers=max(0, args.max_numbers))
    print('\nCONCLUSÃO: este arquivo não valida cobrança nem altera qualquer análise.')


if __name__ == '__main__':
    main()
