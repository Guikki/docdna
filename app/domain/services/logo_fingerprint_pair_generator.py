from __future__ import annotations

from itertools import combinations, product
from typing import Any

from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.models.logo_fingerprint_pair import (
    LogoFingerprintPair,
)


class LogoFingerprintPairGenerator:
    """
    Gera pares de fingerprints de logo pertencentes
    a documentos distintos.

    Regras:

    - não compara um documento com ele mesmo;
    - não gera pares invertidos;
    - ignora análises sem ID válido;
    - ignora análises sem fingerprints de logo;
    - ignora objetos que não sejam LogoFingerprint;
    - considera apenas uma análise para cada ID de documento.
    """

    def generate(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[LogoFingerprintPair]:
        valid_analyses = self._collect_valid_analyses(
            analyses
        )

        pairs: list[LogoFingerprintPair] = []

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

            first_logos = first_analysis[
                "logo_fingerprints"
            ]

            second_logos = second_analysis[
                "logo_fingerprints"
            ]

            for first_logo, second_logo in product(
                first_logos,
                second_logos,
            ):
                pairs.append(
                    LogoFingerprintPair(
                        first_document_id=first_document_id,
                        second_document_id=second_document_id,
                        first_logo=first_logo,
                        second_logo=second_logo,
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
            if not isinstance(
                analysis,
                dict,
            ):
                continue

            document_id = self._extract_document_id(
                analysis
            )

            if not document_id:
                continue

            if document_id in analyses_by_document_id:
                continue

            logo_fingerprints = (
                self._extract_logo_fingerprints(
                    analysis
                )
            )

            if not logo_fingerprints:
                continue

            analyses_by_document_id[document_id] = {
                "document_id": document_id,
                "logo_fingerprints": logo_fingerprints,
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
            analysis.get(
                "document_id",
                "",
            ),
        )

        return str(
            value or ""
        ).strip()

    @staticmethod
    def _extract_logo_fingerprints(
        analysis: dict[str, Any],
    ) -> list[LogoFingerprint]:
        raw_fingerprints = analysis.get(
            "logo_fingerprints",
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
                LogoFingerprint,
            )
        ]