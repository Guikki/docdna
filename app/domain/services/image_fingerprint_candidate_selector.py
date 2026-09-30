from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.image_fingerprint_candidate_selection import (
    ImageFingerprintCandidateSelectionResult,
    ImageFingerprintCandidateSelectionStats,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.services.image_fingerprint_match_classifier import (
    ImageFingerprintMatchClassifier,
)


@dataclass(
    frozen=True,
    slots=True,
)
class _FingerprintOccurrence:
    """
    Representa uma ocorrência de fingerprint durante a construção
    dos índices temporários de seleção.

    sequence preserva uma ordem determinística dentro da execução.
    """

    sequence: int
    document_id: str
    fingerprint: ImageFingerprint
    perceptual_hash: str
    perceptual_hash_bits: int
    image_hash: str | None


class ImageFingerprintCandidateSelector:
    """
    Seleciona fingerprints que merecem comparação técnica profunda.

    A seleção preserva dois caminhos capazes de gerar findings:

    1. igualdade criptográfica por SHA-256;
    2. proximidade perceptual suficiente para atingir o menor
       threshold atualmente aceito pelo classificador.

    A busca perceptual utiliza Multi-Index Hashing.

    Para uma distância máxima R, o hash é dividido em R + 1
    segmentos. Se dois hashes diferirem em no máximo R bits,
    pelo menos um segmento necessariamente será idêntico.

    Assim, fingerprints que podem atingir o threshold não precisam
    ser encontrados por uma busca global O(n²).
    """

    def __init__(
        self,
        *,
        minimum_similarity: float | None = None,
    ) -> None:
        if minimum_similarity is None:
            minimum_similarity = (
                ImageFingerprintMatchClassifier
                .MODERATE_VISUAL_SIMILARITY
            )

        if (
            not isinstance(
                minimum_similarity,
                (int, float),
            )
            or isinstance(
                minimum_similarity,
                bool,
            )
        ):
            raise TypeError(
                "minimum_similarity deve ser numérico."
            )

        minimum_similarity = float(
            minimum_similarity
        )

        if not (
            0.0
            < minimum_similarity
            <= 1.0
        ):
            raise ValueError(
                "minimum_similarity deve estar "
                "entre zero e um."
            )

        self._minimum_similarity = (
            minimum_similarity
        )

    def select(
        self,
        analyses: list[
            dict[str, Any]
        ],
    ) -> ImageFingerprintCandidateSelectionResult:
        occurrences, document_counts = (
            self._collect_occurrences(
                analyses
            )
        )

        potential_pairs = (
            self._calculate_potential_pairs(
                document_counts
            )
        )

        sha256_index: dict[
            str,
            list[_FingerprintOccurrence],
        ] = {}

        perceptual_index: dict[
            tuple[
                int,
                int,
                int,
                str,
            ],
            list[_FingerprintOccurrence],
        ] = {}

        selected_pairs: list[
            ImageFingerprintPair
        ] = []

        seen_pair_keys: set[
            tuple[int, int]
        ] = set()

        exact_sha256_pairs = 0
        perceptual_only_pairs = 0

        for occurrence in occurrences:
            candidate_occurrences: dict[
                int,
                _FingerprintOccurrence,
            ] = {}

            if occurrence.image_hash is not None:
                for candidate in (
                    sha256_index.get(
                        occurrence.image_hash,
                        [],
                    )
                ):
                    candidate_occurrences[
                        candidate.sequence
                    ] = candidate

            segment_keys = (
                self._build_segment_keys(
                    occurrence.perceptual_hash
                )
            )

            for segment_key in segment_keys:
                for candidate in (
                    perceptual_index.get(
                        segment_key,
                        [],
                    )
                ):
                    candidate_occurrences[
                        candidate.sequence
                    ] = candidate

            for candidate_sequence in sorted(
                candidate_occurrences
            ):
                candidate = (
                    candidate_occurrences[
                        candidate_sequence
                    ]
                )

                if (
                    candidate.document_id
                    == occurrence.document_id
                ):
                    continue

                pair_key = (
                    candidate.sequence,
                    occurrence.sequence,
                )

                if pair_key in seen_pair_keys:
                    continue

                exact_sha256_match = (
                    self._has_exact_sha256_match(
                        candidate,
                        occurrence,
                    )
                )

                perceptual_candidate = (
                    self._is_perceptual_candidate(
                        candidate,
                        occurrence,
                    )
                )

                if (
                    not exact_sha256_match
                    and not perceptual_candidate
                ):
                    continue

                seen_pair_keys.add(
                    pair_key
                )

                selected_pairs.append(
                    ImageFingerprintPair(
                        first_document_id=(
                            candidate.document_id
                        ),
                        second_document_id=(
                            occurrence.document_id
                        ),
                        first_image=(
                            candidate.fingerprint
                        ),
                        second_image=(
                            occurrence.fingerprint
                        ),
                    )
                )

                if exact_sha256_match:
                    exact_sha256_pairs += 1
                else:
                    perceptual_only_pairs += 1

            if occurrence.image_hash is not None:
                sha256_index.setdefault(
                    occurrence.image_hash,
                    [],
                ).append(
                    occurrence
                )

            for segment_key in segment_keys:
                perceptual_index.setdefault(
                    segment_key,
                    [],
                ).append(
                    occurrence
                )

        candidate_pairs = len(
            selected_pairs
        )

        reduction_ratio = (
            self._calculate_reduction_ratio(
                potential_pairs=(
                    potential_pairs
                ),
                candidate_pairs=(
                    candidate_pairs
                ),
            )
        )

        return (
            ImageFingerprintCandidateSelectionResult(
                pairs=tuple(
                    selected_pairs
                ),
                stats=(
                    ImageFingerprintCandidateSelectionStats(
                        documents_total=len(
                            document_counts
                        ),
                        fingerprints_total=len(
                            occurrences
                        ),
                        potential_cross_document_pairs=(
                            potential_pairs
                        ),
                        candidate_pairs=(
                            candidate_pairs
                        ),
                        exact_sha256_pairs=(
                            exact_sha256_pairs
                        ),
                        perceptual_only_pairs=(
                            perceptual_only_pairs
                        ),
                        reduction_ratio=(
                            reduction_ratio
                        ),
                    )
                ),
            )
        )

    def _collect_occurrences(
        self,
        analyses: list[
            dict[str, Any]
        ],
    ) -> tuple[
        list[_FingerprintOccurrence],
        dict[str, int],
    ]:
        occurrences: list[
            _FingerprintOccurrence
        ] = []

        document_counts: dict[
            str,
            int,
        ] = {}

        processed_document_ids: set[
            str
        ] = set()

        for analysis in analyses:
            if not isinstance(
                analysis,
                dict,
            ):
                continue

            document_id = (
                self._extract_document_id(
                    analysis
                )
            )

            if not document_id:
                continue

            if (
                document_id
                in processed_document_ids
            ):
                continue

            fingerprints = (
                self._extract_image_fingerprints(
                    analysis
                )
            )

            if not fingerprints:
                continue

            processed_document_ids.add(
                document_id
            )

            document_counts[
                document_id
            ] = len(
                fingerprints
            )

            for fingerprint in fingerprints:
                perceptual_hash = (
                    self._normalize_required_hash(
                        fingerprint.perceptual_hash,
                        hash_name=(
                            "perceptual_hash"
                        ),
                    )
                )

                occurrences.append(
                    _FingerprintOccurrence(
                        sequence=len(
                            occurrences
                        ),
                        document_id=(
                            document_id
                        ),
                        fingerprint=(
                            fingerprint
                        ),
                        perceptual_hash=(
                            perceptual_hash
                        ),
                        perceptual_hash_bits=(
                            len(
                                perceptual_hash
                            )
                            * 4
                        ),
                        image_hash=(
                            self._normalize_optional_hash(
                                fingerprint.image_hash,
                                hash_name=(
                                    "image_hash"
                                ),
                            )
                        ),
                    )
                )

        return (
            occurrences,
            document_counts,
        )

    def _build_segment_keys(
        self,
        perceptual_hash: str,
    ) -> tuple[
        tuple[
            int,
            int,
            int,
            str,
        ],
        ...,
    ]:
        total_bits = (
            len(perceptual_hash)
            * 4
        )

        maximum_distance = (
            self._maximum_hamming_distance(
                total_bits
            )
        )

        partition_count = (
            maximum_distance
            + 1
        )

        bit_string = format(
            int(
                perceptual_hash,
                16,
            ),
            f"0{total_bits}b",
        )

        base_size = (
            total_bits
            // partition_count
        )

        remainder = (
            total_bits
            % partition_count
        )

        keys: list[
            tuple[
                int,
                int,
                int,
                str,
            ]
        ] = []

        start = 0

        for partition_index in range(
            partition_count
        ):
            segment_size = (
                base_size
                + (
                    1
                    if partition_index
                    < remainder
                    else 0
                )
            )

            end = (
                start
                + segment_size
            )

            segment = (
                bit_string[
                    start:end
                ]
            )

            keys.append(
                (
                    total_bits,
                    partition_count,
                    partition_index,
                    segment,
                )
            )

            start = end

        return tuple(
            keys
        )

    def _is_perceptual_candidate(
        self,
        first: _FingerprintOccurrence,
        second: _FingerprintOccurrence,
    ) -> bool:
        if (
            first.perceptual_hash_bits
            != second.perceptual_hash_bits
        ):
            return False

        maximum_distance = (
            self._maximum_hamming_distance(
                first.perceptual_hash_bits
            )
        )

        distance = (
            int(
                first.perceptual_hash,
                16,
            )
            ^ int(
                second.perceptual_hash,
                16,
            )
        ).bit_count()

        return (
            distance
            <= maximum_distance
        )

    @staticmethod
    def _has_exact_sha256_match(
        first: _FingerprintOccurrence,
        second: _FingerprintOccurrence,
    ) -> bool:
        if (
            first.image_hash is None
            or second.image_hash is None
        ):
            return False

        return (
            first.image_hash
            == second.image_hash
        )

    def _maximum_hamming_distance(
        self,
        total_bits: int,
    ) -> int:
        """
        Calcula a maior distância inteira que ainda satisfaz
        o threshold de similaridade configurado.

        A mesma fórmula utilizada pelo comparador é preservada:

            similaridade = 1 - distância / total_bits
        """
        allowed_distance = (
            total_bits
            * (
                1.0
                - self._minimum_similarity
            )
        )

        return max(
            0,
            floor(
                allowed_distance
                + 1e-12
            ),
        )

    @staticmethod
    def _calculate_potential_pairs(
        document_counts: dict[
            str,
            int,
        ],
    ) -> int:
        """
        Calcula o produto cruzado potencial entre documentos sem
        construir nenhum objeto ImageFingerprintPair.
        """
        total_fingerprints = sum(
            document_counts.values()
        )

        same_document_relations = sum(
            count * count
            for count in (
                document_counts.values()
            )
        )

        return (
            (
                total_fingerprints
                * total_fingerprints
                - same_document_relations
            )
            // 2
        )

    @staticmethod
    def _calculate_reduction_ratio(
        *,
        potential_pairs: int,
        candidate_pairs: int,
    ) -> float:
        if potential_pairs <= 0:
            return 0.0

        return (
            1.0
            - (
                candidate_pairs
                / potential_pairs
            )
        )

    @staticmethod
    def _extract_document_id(
        analysis: dict[
            str,
            Any,
        ],
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
    def _extract_image_fingerprints(
        analysis: dict[
            str,
            Any,
        ],
    ) -> list[
        ImageFingerprint
    ]:
        values = analysis.get(
            "image_fingerprints",
            [],
        )

        if not isinstance(
            values,
            (list, tuple),
        ):
            return []

        return [
            value
            for value in values
            if isinstance(
                value,
                ImageFingerprint,
            )
        ]

    @staticmethod
    def _normalize_required_hash(
        value: str,
        *,
        hash_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{hash_name} deve ser uma string."
            )

        normalized = (
            value.strip().lower()
        )

        if not normalized:
            raise ValueError(
                f"{hash_name} não pode ser vazio."
            )

        try:
            int(
                normalized,
                16,
            )
        except ValueError as error:
            raise ValueError(
                f"{hash_name} deve ser hexadecimal."
            ) from error

        return normalized

    @classmethod
    def _normalize_optional_hash(
        cls,
        value: str | None,
        *,
        hash_name: str,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{hash_name} deve ser uma string."
            )

        if not value.strip():
            return None

        return cls._normalize_required_hash(
            value,
            hash_name=hash_name,
        )