
"""CF-QA 003.9.5: concilia evidencias tipograficas com matrizes QR confirmadas.

Nao decodifica, nao reabre PDFs e nao altera o detector TinyTextDetector.
Somente retira do conjunto de alertas tipograficos spans que pertencem
inequivocamente a um grupo de QR com payload igual ao QR visual associado.
O texto nativo permanece no documento e o achado QR permanece separado.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from math import isfinite
from typing import Any, Iterable

from app.domain.concealment.models.visual_concealment_analysis import (
    VisualConcealmentAnalysis,
)


class QrVisualConcealmentCorrelator:
    """Concilia resultados existentes sem executar novamente os detectores."""

    def correlate(
        self,
        *,
        analysis: VisualConcealmentAnalysis,
        normalized_document: Any,
        qr_structural_findings: Iterable[dict[str, Any]],
    ) -> VisualConcealmentAnalysis:
        if not isinstance(analysis, VisualConcealmentAnalysis):
            raise TypeError(
                "analysis must be a VisualConcealmentAnalysis."
            )

        evidences = analysis.tiny_text_evidences

        if not evidences or normalized_document is None:
            return analysis

        # O TinyTextDetector registra uma evidencia por TextSpan,
        # preservando sua ordem. Sem correspondencia comprovada,
        # nenhuma evidencia pode ser excluida.
        spans = self._matched_source_spans(
            normalized_document,
            evidences,
        )

        if spans is None:
            return analysis

        all_spans = tuple(
            span
            for page in (
                getattr(normalized_document, "pages", None) or ()
            )
            for span in (
                getattr(page, "text_spans", None) or ()
            )
        )

        confirmed_span_ids: set[int] = set()

        for finding in qr_structural_findings or ():
            confirmed_span_ids.update(
                self._confirmed_group_span_ids(
                    finding,
                    all_spans,
                )
            )

        if not confirmed_span_ids:
            return analysis

        kept = tuple(
            evidence
            for span, evidence in zip(spans, evidences)
            if id(span) not in confirmed_span_ids
        )

        if len(kept) == len(evidences):
            return analysis

        return replace(
            analysis,
            tiny_text_evidences=kept,
        )

    @staticmethod
    def _matched_source_spans(
        document: Any,
        evidences: tuple,
    ) -> tuple | None:
        thresholds = set()

        for evidence in evidences:
            metadata = getattr(
                evidence,
                "metadata",
                None,
            )

            if (
                not metadata
                or getattr(evidence, "detector", None)
                != "tiny_text"
            ):
                return None

            try:
                threshold = float(
                    metadata["maximum_font_size"]
                )
            except (KeyError, TypeError, ValueError):
                return None

            if not isfinite(threshold) or threshold <= 0:
                return None

            thresholds.add(threshold)

        if len(thresholds) != 1:
            return None

        threshold = next(iter(thresholds))
        eligible = []

        for page in (
            getattr(document, "pages", None) or ()
        ):
            for span in (
                getattr(page, "text_spans", None) or ()
            ):
                font = getattr(span, "font", None)
                text = getattr(span, "text", None)

                if (
                    not isinstance(text, str)
                    or not text.strip()
                    or font is None
                ):
                    continue

                try:
                    size = float(font.size)
                except (
                    AttributeError,
                    TypeError,
                    ValueError,
                ):
                    continue

                if isfinite(size) and size < threshold:
                    eligible.append(span)

        if len(eligible) != len(evidences):
            return None

        for span, evidence in zip(eligible, evidences):
            metadata = evidence.metadata

            if (
                evidence.page_number
                != getattr(span, "page_number", None)
                or evidence.original_excerpt
                != " ".join(span.text.split())[:500]
                or metadata.get("font_name")
                != getattr(span.font, "name", None)
                or metadata.get("font_size")
                != getattr(span.font, "size", None)
            ):
                return None

        return tuple(eligible)

    @classmethod
    def _confirmed_group_span_ids(
        cls,
        group: Any,
        spans: tuple,
    ) -> set[int]:
        if (
            not isinstance(group, dict)
            or group.get("truncated")
        ):
            return set()

        validation = group.get(
            "qr_matrix_validation"
        )

        if (
            group.get("code")
            != "QR_STRUCTURAL_SPATIAL_ASSOCIATION"
            or group.get("qr_payload_equal") is not True
            or not group.get("linked_qr_codes")
            or not isinstance(validation, dict)
            or validation.get("status")
            != "CONFIRMED_PAYLOAD_MATCH"
            or validation.get(
                "payload_equal_to_linked_qr"
            ) is not True
        ):
            return set()

        box = cls._bounds(
            group.get("bounding_box_pdf_points")
        )

        if box is None:
            return set()

        page = group.get("page_number")
        font_name = group.get("font_name")

        if (
            type(page) is not int
            or not isinstance(font_name, str)
            or not font_name
        ):
            return set()

        members = []

        for span in spans:
            if (
                getattr(span, "page_number", None)
                != page
            ):
                continue

            font = getattr(
                getattr(span, "font", None),
                "name",
                None,
            )

            if (
                not isinstance(font, str)
                or font.casefold()
                != font_name.casefold()
            ):
                continue

            text = getattr(span, "text", None)

            if not cls._binary(text):
                continue

            sb = cls._span_bounds(span)

            if sb is None:
                continue

            cx = (sb[0] + sb[2]) / 2
            cy = (sb[1] + sb[3]) / 2

            if (
                box[0] <= cx <= box[2]
                and box[1] <= cy <= box[3]
            ):
                members.append((span, sb))

        members.sort(
            key=lambda item: (
                item[1][1],
                item[1][0],
            )
        )

        raw = "".join(
            span.text
            for span, _ in members
        )

        if (
            not members
            or len(members) != group.get("span_count")
            or len(raw) != group.get("raw_length")
            or sha256(
                raw.encode(
                    "utf-8",
                    errors="replace",
                )
            ).hexdigest()
            != group.get("raw_sha256")
        ):
            return set()

        return {
            id(span)
            for span, _ in members
        }

    @staticmethod
    def _binary(text: Any) -> bool:
        if not isinstance(text, str):
            return False

        bits = "".join(text.split())

        return (
            len(bits) >= 32
            and all(ch in "01" for ch in bits)
        )

    @staticmethod
    def _bounds(
        value: Any,
    ) -> tuple[float, float, float, float] | None:
        try:
            left, top, right, bottom = (
                float(v)
                for v in value
            )
        except (TypeError, ValueError):
            return None

        if (
            all(
                map(
                    isfinite,
                    (left, top, right, bottom),
                )
            )
            and left < right
            and top < bottom
        ):
            return left, top, right, bottom

        return None

    @classmethod
    def _span_bounds(
        cls,
        span: Any,
    ) -> tuple[float, float, float, float] | None:
        bbox = getattr(
            span,
            "bounding_box",
            None,
        )

        if bbox is None:
            return None

        try:
            return cls._bounds(
                (
                    bbox.left,
                    bbox.top,
                    bbox.right,
                    bbox.bottom,
                )
            )
        except AttributeError:
            return None
