"""Corrobora uma linha numérica com texto nativo POSICIONADO do próprio PDF.

Não modifica o OCR, não estima dígitos ausentes e não verifica autenticidade.
A confirmação exige conteúdo integral, ocorrência espacial única e página certa.
Utilizado somente como segunda fonte quando o OCR é pouco confiante.
"""
from __future__ import annotations

import re
from math import isfinite
from pathlib import Path

import pymupdf


class NativeNumericLineCorroborator:
    """Confirma que a camada textual contém a mesma sequência e região."""

    _MAX_WORD_VERTICAL_DELTA_PT = 6.0
    _MAX_WORD_HORIZONTAL_GAP_PT = 35.0
    _MIN_HORIZONTAL_OVERLAP = 0.65
    _MAX_VERTICAL_GAP_PX = 24.0
    _REGION_MARGIN_PT = 20.0
    _NUMERIC_FRAGMENT = re.compile(r"^[\d\s.,/\-]+$", re.ASCII)

    def confirms(
        self,
        *,
        pdf_path: str,
        page_number: int,
        expected_digits: str,
        ocr_left: float,
        ocr_top: float,
        ocr_width: float,
        ocr_height: float,
    ) -> bool:
        """O OCR foi renderizado com Matrix(2, 2); nativo usa pontos PDF.

        Em PDFs rotacionados a correspondência simples de coordenadas não é
        confiável e o método retorna False em vez de inferir uma posição.
        """
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
            or not expected_digits.isascii()
            or not expected_digits.isdigit()
            or len(expected_digits) not in (47, 48)
        ):
            return False

        values = (ocr_left, ocr_top, ocr_width, ocr_height)
        try:
            x, y, w, h = (float(value) for value in values)
        except (ValueError, TypeError):
            return False
        if not all(isfinite(v) for v in (x, y, w, h)) or min(x, y) < 0 or min(w, h) <= 0:
            return False

        if not pdf_path or not Path(pdf_path).is_file():
            return False

        try:
            with pymupdf.open(pdf_path) as document:
                if page_number > len(document):
                    return False
                page = document[page_number - 1]
                if page.rotation != 0:
                    return False
                native_rect = pymupdf.Rect(x / 2, y / 2, (x + w) / 2, (y + h) / 2)
                expanded = pymupdf.Rect(
                    native_rect.x0 - self._REGION_MARGIN_PT,
                    native_rect.y0 - self._REGION_MARGIN_PT,
                    native_rect.x1 + self._REGION_MARGIN_PT,
                    native_rect.y1 + self._REGION_MARGIN_PT,
                )
                words = page.get_text("words", sort=True)
                fragments = []
                for word in words:
                    if len(word) < 5:
                        continue
                    box = pymupdf.Rect(*word[:4])
                    token = str(word[4])
                    if not box.intersects(expanded) or not self._NUMERIC_FRAGMENT.fullmatch(token):
                        continue
                    digits = "".join(ch for ch in token if "0" <= ch <= "9")
                    if digits:
                        fragments.append((box, digits))
                return self._has_unique_positioned_match(fragments, expected_digits, native_rect)
        except (OSError, ValueError, RuntimeError, AttributeError):
            # Impossibilidade de ler o PDF não autoriza criar evidência.
            return False

    def _has_unique_positioned_match(self, fragments, expected: str, ocr_rect) -> bool:
        if not fragments:
            return False
        fragments.sort(key=lambda item: (item[0].y0, item[0].x0))
        rows: list[list[tuple]] = []
        for item in fragments:
            cy = (item[0].y0 + item[0].y1) / 2
            group = next((
                group for group in rows
                if abs(cy - (group[0][0].y0 + group[0][0].y1) / 2)
                <= self._MAX_WORD_VERTICAL_DELTA_PT
            ), None)
            if group is None:
                rows.append([item])
            else:
                group.append(item)
        matches: set[tuple[float, float, float, float]] = set()
        for row in rows:
            row.sort(key=lambda item: item[0].x0)
            for start in range(len(row)):
                assembled = ""
                selected = []
                previous = None
                for rect, digits in row[start:]:
                    if previous is not None and rect.x0 - previous.x1 > self._MAX_WORD_HORIZONTAL_GAP_PT:
                        break
                    assembled += digits
                    selected.append(rect)
                    previous = rect
                    if not expected.startswith(assembled):
                        break
                    if assembled == expected:
                        candidate_rect = pymupdf.Rect(
                            min(r.x0 for r in selected),
                            min(r.y0 for r in selected),
                            max(r.x1 for r in selected),
                            max(r.y1 for r in selected),
                        )
                        if self._aligned(candidate_rect, ocr_rect):
                            matches.add(tuple(round(v, 2) for v in candidate_rect))
                        break
        return len(matches) == 1

    def _aligned(self, found, expected) -> bool:
        overlap = max(0.0, min(found.x1, expected.x1) - max(found.x0, expected.x0))
        width = min(found.width, expected.width)
        if width <= 0 or overlap / width < self._MIN_HORIZONTAL_OVERLAP:
            return False
        vertical_gap = max(0.0, found.y0 - expected.y1, expected.y0 - found.y1)
        return vertical_gap * 2 <= self._MAX_VERTICAL_GAP_PX
