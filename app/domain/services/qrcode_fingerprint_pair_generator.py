from __future__ import annotations

from itertools import combinations, product
from typing import Any

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.qrcode_fingerprint_pair import (
    QRCodeFingerprintPair,
)


class QRCodeFingerprintPairGenerator:
    """
    Gera pares de fingerprints de QR Code pertencentes
    a documentos distintos.

    Regras:

    - não compara um documento com ele mesmo;
    - não gera pares invertidos;
    - ignora análises sem ID válido;
    - ignora análises sem fingerprints de QR Code;
    - ignora objetos que não sejam QRCodeFingerprint;
    - considera apenas uma análise para cada ID de documento.
    """

    def generate(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[QRCodeFingerprintPair]:
        valid_analyses = self._collect_valid_analyses(
            analyses
        )

        pairs: list[QRCodeFingerprintPair] = []

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

            first_qrcodes = first_analysis[
                "qrcode_fingerprints"
            ]

            second_qrcodes = second_analysis[
                "qrcode_fingerprints"
            ]

            for first_qrcode, second_qrcode in product(
                first_qrcodes,
                second_qrcodes,
            ):
                pairs.append(
                    QRCodeFingerprintPair(
                        first_document_id=first_document_id,
                        second_document_id=second_document_id,
                        first_qrcode=first_qrcode,
                        second_qrcode=second_qrcode,
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

            qrcode_fingerprints = (
                self._extract_qrcode_fingerprints(
                    analysis
                )
            )

            if not qrcode_fingerprints:
                continue

            analyses_by_document_id[document_id] = {
                "document_id": document_id,
                "qrcode_fingerprints": qrcode_fingerprints,
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
    def _extract_qrcode_fingerprints(
        analysis: dict[str, Any],
    ) -> list[QRCodeFingerprint]:
        raw_fingerprints = analysis.get(
            "qrcode_fingerprints",
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
                QRCodeFingerprint,
            )
        ]