from __future__ import annotations

import mimetypes
from typing import Any

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.readers.image_reader import ImageReader
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.observability.performance_timer import PerformanceTimer
from app.services.image_fingerprint_builder import ImageFingerprintBuilder
from app.services.image_hash_analyzer import ImageHashAnalyzer


class ImageFingerprintProcessor:
    """
    Coordena a geração de fingerprints das imagens extraídas
    de um documento.

    A instrumentação desta classe decompõe o custo de processamento
    sem alterar o contrato funcional do método process().
    """

    def __init__(
        self,
        reader: ImageReader | None = None,
        analyzer: ImageHashAnalyzer | None = None,
        builder: ImageFingerprintBuilder | None = None,
    ) -> None:
        self._reader = reader or ImageReader()
        self._analyzer = analyzer or ImageHashAnalyzer()
        self._builder = builder or ImageFingerprintBuilder()
        self._performance_report: dict | None = None

    @property
    def performance_report(
        self,
    ) -> dict | None:
        return self._performance_report

    def process(
        self,
        source: str,
        confidence: ConfidenceScore | None = None,
    ) -> list[ImageFingerprint]:
        """
        Processa todas as imagens extraídas de um documento.

        A confiança padrão é 1.0 porque, neste estágio, ela representa
        apenas a confiança técnica na extração da imagem, e não uma
        classificação de autenticidade ou fraude.
        """

        timer = PerformanceTimer()
        hash_stage_totals: dict[
            str,
            dict[str, float | int],
        ] = {}

        try:
            with timer.measure(
                "image_fp_extraction"
            ):
                images = (
                    self._reader.read(
                        source
                    )
                )

            extraction_confidence = (
                confidence
                or ConfidenceScore(1.0)
            )

            fingerprints: list[
                ImageFingerprint
            ] = []

            for image in images:
                try:
                    analysis = (
                        self._analyzer.analyze(
                            image
                        )
                    )

                finally:
                    self._accumulate_analyzer_report(
                        accumulator=(
                            hash_stage_totals
                        ),
                        report=getattr(
                            self._analyzer,
                            "performance_report",
                            None,
                        ),
                    )

                with timer.measure(
                    "image_fp_build"
                ):
                    fingerprints.append(
                        self._build_fingerprint(
                            image=image,
                            confidence=(
                                extraction_confidence
                            ),
                            analysis=analysis,
                        )
                    )

            return fingerprints

        finally:
            self._performance_report = (
                self._build_performance_report(
                    timer_report=(
                        timer.to_dict()
                    ),
                    hash_stage_totals=(
                        hash_stage_totals
                    ),
                )
            )

    def _process_image(
        self,
        image: DocumentImage,
        confidence: ConfidenceScore,
    ) -> ImageFingerprint:
        """
        Mantém o contrato interno anterior para compatibilidade
        com testes e chamadas existentes.
        """

        analysis = self._analyzer.analyze(
            image
        )

        return self._build_fingerprint(
            image=image,
            confidence=confidence,
            analysis=analysis,
        )

    def _build_fingerprint(
        self,
        *,
        image: DocumentImage,
        confidence: ConfidenceScore,
        analysis,
    ) -> ImageFingerprint:
        location = self._create_location(
            image
        )

        mime_type = self._detect_mime_type(
            image
        )

        return self._builder.build_from_analysis(
            image=image,
            location=location,
            confidence=confidence,
            analysis=analysis,
            mime_type=mime_type,
            description=(
                self._create_description(
                    image
                )
            ),
        )

    @staticmethod
    def _accumulate_analyzer_report(
        *,
        accumulator: dict[
            str,
            dict[str, float | int],
        ],
        report: dict | None,
    ) -> None:
        if not report:
            return

        stages = report.get(
            "stages",
            {},
        )

        if not isinstance(
            stages,
            dict,
        ):
            return

        for (
            stage_name,
            stage_data,
        ) in stages.items():
            if not isinstance(
                stage_data,
                dict,
            ):
                continue

            current = accumulator.setdefault(
                stage_name,
                {
                    "duration_seconds": 0.0,
                    "calls": 0,
                },
            )

            current[
                "duration_seconds"
            ] = float(
                current[
                    "duration_seconds"
                ]
            ) + float(
                stage_data.get(
                    "duration_seconds",
                    0.0,
                )
                or 0.0
            )

            current[
                "calls"
            ] = int(
                current[
                    "calls"
                ]
            ) + int(
                stage_data.get(
                    "calls",
                    0,
                )
                or 0
            )

    @staticmethod
    def _build_performance_report(
        *,
        timer_report: dict,
        hash_stage_totals: dict[
            str,
            dict[str, float | int],
        ],
    ) -> dict:
        total_seconds = float(
            timer_report.get(
                "total_seconds",
                0.0,
            )
            or 0.0
        )

        timer_stages = timer_report.get(
            "stages",
            {},
        )

        ordered_stages: dict[
            str,
            dict[str, Any],
        ] = {}

        extraction = timer_stages.get(
            "image_fp_extraction"
        )

        if isinstance(
            extraction,
            dict,
        ):
            ordered_stages[
                "image_fp_extraction"
            ] = dict(extraction)

        for (
            stage_name,
            stage_data,
        ) in hash_stage_totals.items():
            ordered_stages[
                stage_name
            ] = dict(stage_data)

        build = timer_stages.get(
            "image_fp_build"
        )

        if isinstance(
            build,
            dict,
        ):
            ordered_stages[
                "image_fp_build"
            ] = dict(build)

        for stage_data in ordered_stages.values():
            duration = float(
                stage_data.get(
                    "duration_seconds",
                    0.0,
                )
                or 0.0
            )

            calls = int(
                stage_data.get(
                    "calls",
                    0,
                )
                or 0
            )

            stage_data[
                "duration_seconds"
            ] = round(
                duration,
                6,
            )

            stage_data[
                "calls"
            ] = calls

            stage_data[
                "average_seconds"
            ] = round(
                (
                    duration / calls
                    if calls > 0
                    else 0.0
                ),
                6,
            )

            stage_data[
                "percentage_of_total"
            ] = round(
                (
                    duration
                    / total_seconds
                    * 100.0
                    if total_seconds > 0
                    else 0.0
                ),
                2,
            )

        return {
            "total_seconds": round(
                total_seconds,
                6,
            ),
            "stages": ordered_stages,
        }

    @staticmethod
    def _create_location(
        image: DocumentImage,
    ) -> DocumentLocation:
        """
        Cria uma localização correspondente à área completa da imagem.

        O ImageReader ainda não fornece as coordenadas da imagem na página.
        Portanto, o BoundingBox representa, por enquanto, o espaço interno
        da própria imagem extraída.
        """

        return DocumentLocation(
            page_number=(
                image.page_number
            ),
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=float(
                    image.width
                ),
                height=float(
                    image.height
                ),
            ),
        )

    @staticmethod
    def _detect_mime_type(
        image: DocumentImage,
    ) -> str | None:
        mime_type, _ = (
            mimetypes.guess_type(
                image.filename
            )
        )

        return mime_type

    @staticmethod
    def _create_description(
        image: DocumentImage,
    ) -> str:
        return (
            f"Imagem {image.image_index} extraída da página "
            f"{image.page_number}, xref {image.xref}."
        )
