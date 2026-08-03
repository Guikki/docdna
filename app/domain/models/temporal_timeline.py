from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)


@dataclass(frozen=True)
class TemporalTimeline:
    """
    Representa uma visão organizada das datas detectadas em um documento.

    A timeline não avalia fraude e não produz evidências. Ela apenas
    organiza observações temporais para consumo pelos detectores.
    """

    document_id: str
    dates: tuple[DetectedDate, ...]

    def __post_init__(self) -> None:
        for detected_date in self.dates:
            if detected_date.document_id != self.document_id:
                raise ValueError(
                    "Todas as datas da timeline devem pertencer "
                    "ao mesmo documento."
                )

    @property
    def is_empty(self) -> bool:
        """
        Indica se nenhuma data válida foi detectada.
        """

        return len(self.dates) == 0

    @property
    def total_dates(self) -> int:
        """
        Retorna a quantidade total de datas detectadas.
        """

        return len(self.dates)

    @property
    def earliest_date(self) -> date | None:
        """
        Retorna a menor data encontrada na timeline.
        """

        if self.is_empty:
            return None

        return min(
            detected_date.value
            for detected_date in self.dates
        )

    @property
    def latest_date(self) -> date | None:
        """
        Retorna a maior data encontrada na timeline.
        """

        if self.is_empty:
            return None

        return max(
            detected_date.value
            for detected_date in self.dates
        )

    def dates_from_source(
        self,
        source: DateSource,
    ) -> tuple[DetectedDate, ...]:
        """
        Retorna somente as datas provenientes da origem informada.
        """

        return tuple(
            detected_date
            for detected_date in self.dates
            if detected_date.source == source
        )

    def dates_from_page(
        self,
        page_number: int,
    ) -> tuple[DetectedDate, ...]:
        """
        Retorna as datas associadas a uma página específica.

        Datas provenientes de metadados normalmente possuem
        page_number igual a None e não aparecerão neste resultado.
        """

        return tuple(
            detected_date
            for detected_date in self.dates
            if detected_date.page_number == page_number
        )

    def dates_with_value(
        self,
        value: date,
    ) -> tuple[DetectedDate, ...]:
        """
        Retorna todas as ocorrências de uma determinada data.

        Uma mesma data pode aparecer em diferentes páginas ou origens,
        como texto nativo, OCR e metadados.
        """

        return tuple(
            detected_date
            for detected_date in self.dates
            if detected_date.value == value
        )

    def distinct_values(self) -> tuple[date, ...]:
        """
        Retorna os valores de data distintos em ordem cronológica.
        """

        return tuple(
            sorted(
                {
                    detected_date.value
                    for detected_date in self.dates
                }
            )
        )

    def has_source(
        self,
        source: DateSource,
    ) -> bool:
        """
        Indica se existe pelo menos uma data da origem informada.
        """

        return any(
            detected_date.source == source
            for detected_date in self.dates
        )