from __future__ import annotations

from itertools import combinations, product
from typing import Any

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)


class ImageFingerprintPairGenerator:
    """
    Gera pares de fingerprints de imagem pertencentes
    a documentos distintos.

    Regras:

    - não compara um documento com ele mesmo;
    - não gera pares invertidos;
    - ignora análises sem ID válido;
    - ignora análises sem fingerprints de imagem;
    - ignora objetos que não sejam ImageFingerprint;
    - considera apenas uma análise para cada ID de documento.
    """

    def generate(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[ImageFingerprintPair]:
        valid_analyses = self._collect_valid_analyses(
            analyses
        )

        pairs: list[ImageFingerprintPair] = []

        for first_analysis, second_analysis in combinations(
            valid_analyses,
            2,
        ):
            first_document_id = first_analysis[
                "document_id"
            ]

            second_document_id = second_analysis[
                "document_id"
            ]

            first_images = first_analysis[
                "image_fingerprints"
            ]

            second_images = second_analysis[
                "image_fingerprints"
            ]

            for first_image, second_image in product(
                first_images,
                second_images,
            ):
                pairs.append(
                    ImageFingerprintPair(
                        first_document_id=first_document_id,
                        second_document_id=second_document_id,
                        first_image=first_image,
                        second_image=second_image,
                    )
                )

        return pairs

    def _collect_valid_analyses(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        analyses_by_document_id: dict[
            str,
            dict[str, Any],
        ] = {}

        for analysis in analyses:
            if not isinstance(analysis, dict):
                continue

            document_id = self._extract_document_id(
                analysis
            )

            if not document_id:
                continue

            if document_id in analyses_by_document_id:
                continue

            image_fingerprints = (
                self._extract_image_fingerprints(
                    analysis
                )
            )

            if not image_fingerprints:
                continue

            analyses_by_document_id[document_id] = {
                "document_id": document_id,
                "image_fingerprints": image_fingerprints,
            }

        return list(
            analyses_by_document_id.values()
        )

    @staticmethod
    def _extract_document_id(
        analysis: dict[str, Any],
    ) -> str:
        value = analysis.get(
            "id",
            analysis.get("document_id", ""),
        )

        return str(value or "").strip()

    @staticmethod
    def _extract_image_fingerprints(
        analysis: dict[str, Any],
    ) -> list[ImageFingerprint]:
        raw_fingerprints = analysis.get(
            "image_fingerprints",
            [],
        )

        if not isinstance(
            raw_fingerprints,
            (list, tuple),
        ):
            return []

        return [
            fingerprint
            for fingerprint in raw_fingerprints
            if isinstance(
                fingerprint,
                ImageFingerprint,
            )
        ]