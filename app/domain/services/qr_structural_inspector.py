"""CF-QA 003.9.1: correlação conservadora de QR Code e fontes PDF.

Não decodifica a matriz de QR. A aproximação geométrica entre um texto
com fonte sugestiva e um QR visual é SOMENTE uma associação espacial.
Não é evidência de ocultação nem de identidade de payload.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from math import isfinite
from typing import Any, Iterable

from app.domain.services.encoded_content_inspector import EncodedContentInspector
from app.domain.services.qr_matrix_payload_correlator import QrMatrixPayloadCorrelator


class QrStructuralInspector:
    MAX_PAGES = 100
    MAX_SPANS_PER_PAGE = 10000
    MAX_GROUPS_PER_PAGE = 150
    MAX_GROUP_CHARS = 8192
    GROUP_TOLERANCE_POINTS = 16.0

    def __init__(self) -> None:
        self._encoded = EncodedContentInspector()
        self._matrix = QrMatrixPayloadCorrelator()

    def inspect_pdf(self, pdf_path: str, *, barcodes: Iterable[Any] = ()) -> list[dict[str, Any]]:
        """Inspeciona somente a camada nativa, sem OCR de página inteira."""
        import pymupdf

        barcode_items = list(barcodes)
        findings: list[dict[str, Any]] = []
        with pymupdf.open(pdf_path) as document:
            for page_number, page in enumerate(document, start=1):
                if page_number > self.MAX_PAGES:
                    break
                spans = self._candidate_spans(page, page_number)
                groups = self._group(spans)
                for group in groups[:self.MAX_GROUPS_PER_PAGE]:
                    findings.append(self._record(group, barcode_items))
        return findings

    def inspect_spans(
        self, spans: Iterable[dict[str, Any]], *, barcodes: Iterable[Any] = ()
    ) -> list[dict[str, Any]]:
        """Entrada independente do PyMuPDF para regressão e integração futura."""
        barcode_items = list(barcodes)
        return [self._record(g, barcode_items) for g in self._group(list(spans))]

    def _candidate_spans(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        payload = page.get_text("dict")
        items: list[dict[str, Any]] = []
        for block in payload.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if len(items) >= self.MAX_SPANS_PER_PAGE:
                        return items
                    text = str(span.get("text", "") or "")
                    font = str(span.get("font", "") or "")
                    if not text.strip():
                        continue
                    if not (self._encoded._is_qr_font(font) or self._encoded._binary_bits(text)):
                        continue
                    bbox = self._bbox(span.get("bbox"))
                    if bbox is None:
                        continue
                    items.append({
                        "page_number": page_number,
                        "text": text,
                        "font_name": font,
                        "source": "native_pdf_font",
                        "bbox": bbox,
                    })
        return items

    @staticmethod
    def _bbox(raw: Any) -> tuple[float, float, float, float] | None:
        try:
            x0, y0, x1, y1 = [float(n) for n in raw]
        except (TypeError, ValueError):
            return None
        if not all(isfinite(n) for n in (x0, y0, x1, y1)):
            return None
        if x0 >= x1 or y0 >= y1:
            return None
        return (x0, y0, x1, y1)

    @classmethod
    def _group(cls, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Agrupamento espacial limitado; não mescla fontes ou páginas distintas."""
        buckets: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
        for span in spans:
            bbox = cls._bbox(span.get("bbox"))
            if bbox is None:
                continue
            page = span.get("page_number")
            if type(page) is not int or page < 1:
                continue
            item = dict(span)
            item["bbox"] = bbox
            buckets[(page, str(span.get("font_name", "") or ""))].append(item)
        result: list[dict[str, Any]] = []
        for (page, font), items in sorted(buckets.items()):
            items.sort(key=lambda a: (a["bbox"][1], a["bbox"][0]))
            groups: list[dict[str, Any]] = []
            for item in items:
                bbox = item["bbox"]
                chosen = None
                for group in reversed(groups[-100:]):
                    if cls._near(group["bbox"], bbox, cls.GROUP_TOLERANCE_POINTS):
                        chosen = group
                        break
                if chosen is None:
                    groups.append({"page_number": page, "font_name": font,
                                   "bbox": bbox, "texts": [], "span_count": 0, "truncated": False})
                    chosen = groups[-1]
                chosen["bbox"] = cls._union(chosen["bbox"], bbox)
                chosen["span_count"] += 1
                text = str(item.get("text", ""))
                if sum(len(s) for s in chosen["texts"]) + len(text) <= cls.MAX_GROUP_CHARS:
                    chosen["texts"].append(text)
                else:
                    chosen["truncated"] = True
            result.extend(groups)
        return sorted(result, key=lambda r: (r["page_number"], r["bbox"][1], r["bbox"][0]))

    @staticmethod
    def _union(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))

    @staticmethod
    def _near(a: tuple[float, ...], b: tuple[float, ...], margin: float) -> bool:
        return a[0] <= b[2] + margin and b[0] <= a[2] + margin and \
               a[1] <= b[3] + margin and b[1] <= a[3] + margin

    def _record(self, group: dict[str, Any], barcodes: list[Any]) -> dict[str, Any]:
        raw = "".join(group["texts"])
        box = group["bbox"]
        analysis = self._encoded.inspect([{
            "text": raw, "font_name": group["font_name"],
            "page_number": group["page_number"], "source": "native_pdf_font",
            "bounding_box": box,
        }])
        matches = []
        for barcode in barcodes:
            page = self._value(barcode, "page_number")
            fmt = str(self._value(barcode, "format") or "").lower().replace(" ", "")
            if page != group["page_number"] or "qr" not in fmt:
                continue
            barcode_box = self._barcode_bbox(barcode)
            if barcode_box is None or self._intersection_fraction(box, barcode_box) < 0.65:
                continue
            content = str(self._value(barcode, "content") or "")
            matches.append({
                "barcode_index": self._value(barcode, "barcode_index"),
                "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
                "association_type": "GEOMETRIC_ONLY",
            })
        # CF-QA 003.9.5: a geometria é apenas candidata. A equivalência
        # de payload só passa a True após reconstrução + decodificação ZXing
        # + igualdade com o hash de um QR visual vinculado nesta página/região.
        # Não reabre o PDF e não afeta o score ou a análise semântica.
        matrix_result = self._matrix.inspect(group=group, linked_qr_codes=matches)
        return {
            "code": ("QR_STRUCTURAL_SPATIAL_ASSOCIATION" if matches else
                     "QR_FONT_STRUCTURAL_CANDIDATE" if self._encoded._is_qr_font(group["font_name"])
                     else "BINARY_STRUCTURAL_CANDIDATE"),
            "page_number": group["page_number"],
            "font_name": group["font_name"],
            "bounding_box_pdf_points": box,
            "span_count": group["span_count"],
            "raw_sha256": sha256(raw.encode("utf-8", errors="replace")).hexdigest(),
            "raw_length": len(raw),
            "truncated": group["truncated"],
            "qr_font_hint": self._encoded._is_qr_font(group["font_name"]),
            "linked_qr_codes": matches,
            "qr_payload_equal": matrix_result["payload_equal_to_linked_qr"],
            "qr_matrix_validation": matrix_result,
            "visually_concealed": None,  # PDF fonte != conteúdo visualmente oculto
            "decoded_content": analysis[0]["decoded"] if analysis else [],
            "requires_semantic_review": bool(analysis and analysis[0]["decoded"]),
        }

    @staticmethod
    def _value(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    @classmethod
    def _barcode_bbox(cls, barcode: Any) -> tuple[float, ...] | None:
        location = cls._value(barcode, "location")
        bbox = cls._value(location, "bounding_box")
        if bbox is None:
            return None
        try:
            x = float(cls._value(bbox, "x"))
            y = float(cls._value(bbox, "y"))
            w = float(cls._value(bbox, "width"))
            h = float(cls._value(bbox, "height"))
        except (TypeError, ValueError):
            return None
        return cls._bbox((x, y, x + w, y + h))

    @staticmethod
    def _intersection_fraction(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
        height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
        area = width * height
        small = min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
        return area / small if small > 0 else 0.0
