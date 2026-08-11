from __future__ import annotations

from dataclasses import dataclass

from app.frontend.investigations.models.investigation_metric import (
    InvestigationMetric,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)


@dataclass(frozen=True, slots=True)
class InvestigationCard:
    """
    Representa um card de investigação exibido no panorama da análise.

    Este objeto pertence exclusivamente à camada de apresentação.

    Ele não executa detectores, não produz evidências e não decide
    autenticidade ou fraude. Apenas organiza, para o frontend, o
    resultado já produzido pelos verificadores executados.

    Cada card resume uma investigação e fornece a rota para a página
    detalhada correspondente.
    """

    slug: str
    title: str

    status: InvestigationStatus
    status_label: str

    summary: str

    metrics: tuple[InvestigationMetric, ...]

    evidence_count: int

    route: str

    def __post_init__(self) -> None:
        normalized_slug = self._normalize_slug(
            self.slug
        )

        normalized_title = self._normalize_text(
            field_name="title",
            value=self.title,
        )

        normalized_status_label = self._normalize_text(
            field_name="status_label",
            value=self.status_label,
        )

        normalized_summary = self._normalize_text(
            field_name="summary",
            value=self.summary,
        )

        normalized_metrics = self._validate_metrics(
            self.metrics
        )

        normalized_evidence_count = (
            self._validate_evidence_count(
                self.evidence_count
            )
        )

        normalized_route = self._normalize_route(
            self.route
        )

        if not isinstance(
            self.status,
            InvestigationStatus,
        ):
            raise TypeError(
                "InvestigationCard status must be "
                "an InvestigationStatus."
            )

        object.__setattr__(
            self,
            "slug",
            normalized_slug,
        )

        object.__setattr__(
            self,
            "title",
            normalized_title,
        )

        object.__setattr__(
            self,
            "status_label",
            normalized_status_label,
        )

        object.__setattr__(
            self,
            "summary",
            normalized_summary,
        )

        object.__setattr__(
            self,
            "metrics",
            normalized_metrics,
        )

        object.__setattr__(
            self,
            "evidence_count",
            normalized_evidence_count,
        )

        object.__setattr__(
            self,
            "route",
            normalized_route,
        )

    @property
    def has_evidences(self) -> bool:
        """
        Retorna se existem evidências relacionadas ao card.
        """

        return self.evidence_count > 0

    @property
    def metric_count(self) -> int:
        """
        Retorna a quantidade de métricas resumidas do card.
        """

        return len(self.metrics)

    @staticmethod
    def _normalize_slug(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "InvestigationCard slug must be a string."
            )

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError(
                "InvestigationCard slug cannot be empty."
            )

        allowed_characters = set(
            "abcdefghijklmnopqrstuvwxyz0123456789-_"
        )

        if any(
            character not in allowed_characters
            for character in normalized
        ):
            raise ValueError(
                "InvestigationCard slug contains "
                "invalid characters."
            )

        return normalized

    @staticmethod
    def _normalize_text(
        *,
        field_name: str,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"InvestigationCard {field_name} "
                "must be a string."
            )

        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                f"InvestigationCard {field_name} "
                "cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_metrics(
        value: tuple[InvestigationMetric, ...],
    ) -> tuple[InvestigationMetric, ...]:
        if not isinstance(value, tuple):
            raise TypeError(
                "InvestigationCard metrics must be a tuple."
            )

        for index, metric in enumerate(value):
            if not isinstance(
                metric,
                InvestigationMetric,
            ):
                raise TypeError(
                    "InvestigationCard metrics must contain "
                    "only InvestigationMetric instances. "
                    f"Invalid item at index {index}."
                )

        return value

    @staticmethod
    def _validate_evidence_count(
        value: int,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                "InvestigationCard evidence_count "
                "must be an integer."
            )

        if value < 0:
            raise ValueError(
                "InvestigationCard evidence_count "
                "cannot be negative."
            )

        return value

    @staticmethod
    def _normalize_route(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "InvestigationCard route must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "InvestigationCard route cannot be empty."
            )

        if not normalized.startswith("/"):
            raise ValueError(
                "InvestigationCard route must start with '/'."
            )

        return normalized