from __future__ import annotations

from typing import Any

from app.domain.models.batch_finding_summary import (
    BatchFindingSummary,
)


class BatchFindingAggregationService:
    """
    Agrega achados individuais de múltiplas análises.

    O objetivo deste serviço é responder perguntas como:

        Quantos documentos possuem ocultação visual?
        Quantos possuem Prompt Injection?
        Qual a prevalência daquele achado dentro do lote?

    A unidade principal de prevalência é o DOCUMENTO.

    Se um documento possuir dez ocorrências do mesmo tipo,
    ele continua representando apenas um documento afetado.
    """

    PROMPT_INJECTION_CODE = "PROMPT_INJECTION"
    PROMPT_INJECTION_TITLE = "Prompt Injection"

    VISUAL_CONCEALMENT_CODE = "VISUAL_CONCEALMENT"
    VISUAL_CONCEALMENT_TITLE = "Ocultação visual"

    def aggregate(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[BatchFindingSummary]:
        valid_analyses = [
            analysis
            for analysis in analyses
            if self._extract_analysis_id(analysis)
        ]

        total_documents = len(valid_analyses)

        if total_documents == 0:
            return []

        accumulators: dict[
            str,
            dict[str, Any],
        ] = {}

        for analysis in valid_analyses:
            analysis_id = self._extract_analysis_id(
                analysis
            )

            if analysis_id is None:
                continue

            self._aggregate_generic_evidences(
                analysis=analysis,
                analysis_id=analysis_id,
                accumulators=accumulators,
            )

            self._aggregate_prompt_injection(
                analysis=analysis,
                analysis_id=analysis_id,
                accumulators=accumulators,
            )

            self._aggregate_visual_concealment(
                analysis=analysis,
                analysis_id=analysis_id,
                accumulators=accumulators,
            )

        summaries = [
            self._build_summary(
                accumulator=accumulator,
                total_documents=total_documents,
            )
            for accumulator in accumulators.values()
        ]

        summaries.sort(
            key=lambda summary: (
                -summary.affected_documents,
                -summary.prevalence_percentage,
                summary.title.lower(),
            )
        )

        return summaries

    def _aggregate_generic_evidences(
        self,
        *,
        analysis: dict[str, Any],
        analysis_id: str,
        accumulators: dict[str, dict[str, Any]],
    ) -> None:
        evidences = analysis.get(
            "evidences",
            [],
        )

        if not isinstance(
            evidences,
            (list, tuple),
        ):
            return

        for evidence in evidences:
            code = self._normalize_code(
                self._read_value(
                    evidence,
                    "code",
                )
            )

            if not code:
                continue

            title = self._normalize_title(
                self._read_value(
                    evidence,
                    "title",
                )
            )

            if not title:
                title = self._build_title_from_code(
                    code
                )

            confidence = self._normalize_confidence(
                self._read_value(
                    evidence,
                    "confidence",
                )
            )

            self._register_occurrence(
                accumulators=accumulators,
                code=code,
                title=title,
                analysis_id=analysis_id,
                confidence=confidence,
            )

    def _aggregate_prompt_injection(
        self,
        *,
        analysis: dict[str, Any],
        analysis_id: str,
        accumulators: dict[str, dict[str, Any]],
    ) -> None:
        assessment = analysis.get(
            "prompt_injection_assessment"
        )

        if assessment is None:
            return

        evidences = self._read_value(
            assessment,
            "evidences",
        )

        if not evidences:
            return

        normalized_evidences = list(
            evidences
        )

        if not normalized_evidences:
            return

        confidence = self._normalize_confidence(
            self._read_value(
                assessment,
                "score",
            )
        )

        if confidence == 0.0:
            confidence = max(
                (
                    self._normalize_confidence(
                        self._read_value(
                            evidence,
                            "confidence",
                        )
                    )
                    for evidence in normalized_evidences
                ),
                default=0.0,
            )

        for _ in normalized_evidences:
            self._register_occurrence(
                accumulators=accumulators,
                code=self.PROMPT_INJECTION_CODE,
                title=self.PROMPT_INJECTION_TITLE,
                analysis_id=analysis_id,
                confidence=confidence,
            )

    def _aggregate_visual_concealment(
        self,
        *,
        analysis: dict[str, Any],
        analysis_id: str,
        accumulators: dict[str, dict[str, Any]],
    ) -> None:
        concealment_analysis = analysis.get(
            "visual_concealment_analysis"
        )

        if concealment_analysis is None:
            return

        white_text_findings = (
            self._read_value(
                concealment_analysis,
                "white_text_findings",
            )
            or ()
        )

        tiny_text_evidences = (
            self._read_value(
                concealment_analysis,
                "tiny_text_evidences",
            )
            or ()
        )

        findings = [
            *list(white_text_findings),
            *list(tiny_text_evidences),
        ]

        if not findings:
            return

        for finding in findings:
            confidence = self._normalize_confidence(
                self._read_value(
                    finding,
                    "confidence",
                )
            )

            self._register_occurrence(
                accumulators=accumulators,
                code=self.VISUAL_CONCEALMENT_CODE,
                title=self.VISUAL_CONCEALMENT_TITLE,
                analysis_id=analysis_id,
                confidence=confidence,
            )

    def _register_occurrence(
        self,
        *,
        accumulators: dict[str, dict[str, Any]],
        code: str,
        title: str,
        analysis_id: str,
        confidence: float,
    ) -> None:
        if code not in accumulators:
            accumulators[code] = {
                "code": code,
                "title": title,
                "document_ids": set(),
                "occurrence_count": 0,
                "highest_confidence": 0.0,
            }

        accumulator = accumulators[
            code
        ]

        accumulator[
            "document_ids"
        ].add(
            analysis_id
        )

        accumulator[
            "occurrence_count"
        ] += 1

        accumulator[
            "highest_confidence"
        ] = max(
            accumulator[
                "highest_confidence"
            ],
            confidence,
        )

    def _build_summary(
        self,
        *,
        accumulator: dict[str, Any],
        total_documents: int,
    ) -> BatchFindingSummary:
        document_ids = tuple(
            sorted(
                accumulator[
                    "document_ids"
                ]
            )
        )

        affected_documents = len(
            document_ids
        )

        prevalence_percentage = round(
            (
                affected_documents
                / total_documents
                * 100
            ),
            2,
        )

        return BatchFindingSummary(
            code=accumulator["code"],
            title=accumulator["title"],
            affected_documents=(
                affected_documents
            ),
            total_documents=total_documents,
            occurrence_count=(
                accumulator[
                    "occurrence_count"
                ]
            ),
            prevalence_percentage=(
                prevalence_percentage
            ),
            affected_document_ids=(
                document_ids
            ),
            highest_confidence=round(
                accumulator[
                    "highest_confidence"
                ],
                4,
            ),
        )

    def _extract_analysis_id(
        self,
        analysis: dict[str, Any],
    ) -> str | None:
        analysis_id = analysis.get(
            "id"
        )

        if analysis_id is None:
            return None

        normalized = str(
            analysis_id
        ).strip()

        return normalized or None

    def _read_value(
        self,
        source: Any,
        field: str,
    ) -> Any:
        if source is None:
            return None

        if isinstance(
            source,
            dict,
        ):
            return source.get(
                field
            )

        return getattr(
            source,
            field,
            None,
        )

    def _normalize_code(
        self,
        value: Any,
    ) -> str:
        return (
            str(value or "")
            .strip()
            .upper()
        )

    def _normalize_title(
        self,
        value: Any,
    ) -> str:
        return str(
            value or ""
        ).strip()

    def _normalize_confidence(
        self,
        value: Any,
    ) -> float:
        if value is None:
            return 0.0

        try:
            confidence = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        return min(
            max(
                confidence,
                0.0,
            ),
            1.0,
        )

    def _build_title_from_code(
        self,
        code: str,
    ) -> str:
        return (
            code
            .replace("_", " ")
            .strip()
            .title()
        )