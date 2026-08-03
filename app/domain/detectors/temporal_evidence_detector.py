from __future__ import annotations

from datetime import date

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.models.temporal_timeline import (
    TemporalTimeline,
)


class TemporalEvidenceDetector:
    """
    Analisa uma timeline documental e produz evidências temporais.

    O detector não extrai datas e não constrói timelines.
    Ele recebe observações já normalizadas e organizadas.

    Regras iniciais:

    1. data de modificação do PDF anterior à data de criação;
    2. existência de datas futuras;
    3. intervalo temporal excessivamente amplo;
    4. divergência relevante entre datas técnicas e datas declaradas.
    """

    FUTURE_DATE_CODE = "TEMPORAL_FUTURE_DATE"
    INVALID_METADATA_ORDER_CODE = "TEMPORAL_INVALID_METADATA_ORDER"
    EXCESSIVE_RANGE_CODE = "TEMPORAL_EXCESSIVE_RANGE"
    METADATA_CONTENT_DIVERGENCE_CODE = (
        "TEMPORAL_METADATA_CONTENT_DIVERGENCE"
    )

    CREATION_DATE_FIELD = "creationDate"
    MODIFICATION_DATE_FIELD = "modDate"

    def __init__(
        self,
        *,
        maximum_expected_range_days: int = 3650,
        metadata_content_tolerance_days: int = 3650,
    ) -> None:
        if maximum_expected_range_days < 0:
            raise ValueError(
                "O intervalo temporal máximo não pode ser negativo."
            )

        if metadata_content_tolerance_days < 0:
            raise ValueError(
                "A tolerância entre metadados e conteúdo "
                "não pode ser negativa."
            )

        self._maximum_expected_range_days = (
            maximum_expected_range_days
        )

        self._metadata_content_tolerance_days = (
            metadata_content_tolerance_days
        )

    def detect(
        self,
        *,
        timeline: TemporalTimeline,
        reference_date: date | None = None,
    ) -> list[DocumentEvidence]:
        """
        Executa as regras temporais sobre uma timeline.

        A data de referência pode ser informada nos testes ou durante
        uma análise histórica. Quando omitida, utiliza a data atual.
        """

        effective_reference_date = (
            reference_date
            if reference_date is not None
            else date.today()
        )

        evidences: list[DocumentEvidence] = []

        invalid_metadata_order = (
            self._detect_invalid_metadata_order(
                timeline=timeline,
            )
        )

        if invalid_metadata_order is not None:
            evidences.append(invalid_metadata_order)

        future_date_evidence = self._detect_future_dates(
            timeline=timeline,
            reference_date=effective_reference_date,
        )

        if future_date_evidence is not None:
            evidences.append(future_date_evidence)

        excessive_range_evidence = (
            self._detect_excessive_temporal_range(
                timeline=timeline,
            )
        )

        if excessive_range_evidence is not None:
            evidences.append(excessive_range_evidence)

        metadata_content_divergence = (
            self._detect_metadata_content_divergence(
                timeline=timeline,
            )
        )

        if metadata_content_divergence is not None:
            evidences.append(metadata_content_divergence)

        return evidences

    def _detect_invalid_metadata_order(
        self,
        *,
        timeline: TemporalTimeline,
    ) -> DocumentEvidence | None:
        creation_dates = self._metadata_dates(
            timeline=timeline,
            metadata_field=self.CREATION_DATE_FIELD,
        )

        modification_dates = self._metadata_dates(
            timeline=timeline,
            metadata_field=self.MODIFICATION_DATE_FIELD,
        )

        if not creation_dates or not modification_dates:
            return None

        creation_date = min(
            detected.value
            for detected in creation_dates
        )

        modification_date = min(
            detected.value
            for detected in modification_dates
        )

        if modification_date >= creation_date:
            return None

        return DocumentEvidence(
            code=self.INVALID_METADATA_ORDER_CODE,
            title="Ordem temporal inconsistente nos metadados",
            description=(
                "A data de modificação registrada nos metadados "
                "do PDF é anterior à data de criação do arquivo."
            ),
            severity=EvidenceSeverity.HIGH,
            confidence=1.0,
            source="temporal_evidence_detector",
            document_ids=(timeline.document_id,),
            metadata={
                "creation_date": creation_date.isoformat(),
                "modification_date": modification_date.isoformat(),
                "creation_field": self.CREATION_DATE_FIELD,
                "modification_field": self.MODIFICATION_DATE_FIELD,
            },
        )

    def _detect_future_dates(
        self,
        *,
        timeline: TemporalTimeline,
        reference_date: date,
    ) -> DocumentEvidence | None:
        future_dates = tuple(
            detected
            for detected in timeline.dates
            if detected.value > reference_date
        )

        if not future_dates:
            return None

        future_values = sorted(
            {
                detected.value.isoformat()
                for detected in future_dates
            }
        )

        affected_pages = sorted(
            {
                detected.page_number
                for detected in future_dates
                if detected.page_number is not None
            }
        )

        return DocumentEvidence(
            code=self.FUTURE_DATE_CODE,
            title="Data futura identificada",
            description=(
                "Foram identificadas datas posteriores à data "
                "de referência da análise."
            ),
            severity=EvidenceSeverity.MEDIUM,
            confidence=self._minimum_confidence(
                future_dates
            ),
            source="temporal_evidence_detector",
            document_ids=(timeline.document_id,),
            metadata={
                "reference_date": reference_date.isoformat(),
                "future_dates": future_values,
                "occurrence_count": len(future_dates),
                "affected_pages": affected_pages,
                "sources": self._source_values(
                    future_dates
                ),
            },
        )

    def _detect_excessive_temporal_range(
        self,
        *,
        timeline: TemporalTimeline,
    ) -> DocumentEvidence | None:
        earliest_date = timeline.earliest_date
        latest_date = timeline.latest_date

        if earliest_date is None or latest_date is None:
            return None

        interval_days = (
            latest_date - earliest_date
        ).days

        if interval_days <= self._maximum_expected_range_days:
            return None

        return DocumentEvidence(
            code=self.EXCESSIVE_RANGE_CODE,
            title="Amplitude temporal elevada",
            description=(
                "O documento contém datas separadas por um intervalo "
                "superior ao limite esperado para uma única análise "
                "documental."
            ),
            severity=EvidenceSeverity.LOW,
            confidence=1.0,
            source="temporal_evidence_detector",
            document_ids=(timeline.document_id,),
            metadata={
                "earliest_date": earliest_date.isoformat(),
                "latest_date": latest_date.isoformat(),
                "interval_days": interval_days,
                "maximum_expected_range_days": (
                    self._maximum_expected_range_days
                ),
            },
        )

    def _detect_metadata_content_divergence(
        self,
        *,
        timeline: TemporalTimeline,
    ) -> DocumentEvidence | None:
        metadata_dates = tuple(
            detected
            for detected in timeline.dates
            if detected.source == DateSource.PDF_METADATA
        )

        content_dates = tuple(
            detected
            for detected in timeline.dates
            if detected.source
            in {
                DateSource.NATIVE_TEXT,
                DateSource.OCR,
            }
        )

        if not metadata_dates or not content_dates:
            return None

        greatest_difference = 0
        most_distant_metadata: DetectedDate | None = None
        most_distant_content: DetectedDate | None = None

        for metadata_date in metadata_dates:
            for content_date in content_dates:
                difference = abs(
                    (
                        metadata_date.value
                        - content_date.value
                    ).days
                )

                if difference > greatest_difference:
                    greatest_difference = difference
                    most_distant_metadata = metadata_date
                    most_distant_content = content_date

        if (
            greatest_difference
            <= self._metadata_content_tolerance_days
        ):
            return None

        if (
            most_distant_metadata is None
            or most_distant_content is None
        ):
            return None

        return DocumentEvidence(
            code=self.METADATA_CONTENT_DIVERGENCE_CODE,
            title="Divergência entre metadados e conteúdo",
            description=(
                "Foi identificada uma diferença temporal relevante "
                "entre uma data técnica do PDF e uma data declarada "
                "no conteúdo documental."
            ),
            severity=EvidenceSeverity.MEDIUM,
            confidence=min(
                most_distant_metadata.confidence,
                most_distant_content.confidence,
            ),
            source="temporal_evidence_detector",
            document_ids=(timeline.document_id,),
            metadata={
                "metadata_date": (
                    most_distant_metadata.value.isoformat()
                ),
                "metadata_field": (
                    most_distant_metadata.metadata_field
                ),
                "content_date": (
                    most_distant_content.value.isoformat()
                ),
                "content_source": (
                    most_distant_content.source.value
                ),
                "content_page": (
                    most_distant_content.page_number
                ),
                "difference_days": greatest_difference,
                "tolerance_days": (
                    self._metadata_content_tolerance_days
                ),
            },
        )

    def _metadata_dates(
        self,
        *,
        timeline: TemporalTimeline,
        metadata_field: str,
    ) -> tuple[DetectedDate, ...]:
        return tuple(
            detected
            for detected in timeline.dates
            if (
                detected.source == DateSource.PDF_METADATA
                and detected.metadata_field == metadata_field
            )
        )

    def _minimum_confidence(
        self,
        detected_dates: tuple[DetectedDate, ...],
    ) -> float:
        return min(
            detected.confidence
            for detected in detected_dates
        )

    def _source_values(
        self,
        detected_dates: tuple[DetectedDate, ...],
    ) -> list[str]:
        return sorted(
            {
                detected.source.value
                for detected in detected_dates
            }
        )