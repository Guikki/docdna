from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.frontend.investigations.models.investigation_card import (
    InvestigationCard,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)


class InvestigationStatusResolver:
    """
    Resolve o status analítico de apresentação a partir
    dos resultados das investigações de um documento.

    Precedência:

        ALERT
        ATTENTION
        CLEAR
        NOT_EXECUTED

    O resolver não interpreta fraude, autenticidade ou risco
    jurídico. Ele apenas consolida os estados visuais já
    produzidos pelas investigações existentes.
    """

    _PRIORITY = (
        InvestigationStatus.ALERT,
        InvestigationStatus.ATTENTION,
        InvestigationStatus.CLEAR,
        InvestigationStatus.NOT_EXECUTED,
    )

    def resolve(
        self,
        cards: Iterable[
            InvestigationCard | dict[str, Any]
        ],
    ) -> InvestigationStatus:
        normalized_cards = list(cards)

        if not normalized_cards:
            return InvestigationStatus.NOT_EXECUTED

        statuses = [
            self._extract_status(card)
            for card in normalized_cards
        ]

        return self.resolve_statuses(
            statuses
        )

    def resolve_statuses(
        self,
        statuses: Iterable[InvestigationStatus],
    ) -> InvestigationStatus:
        normalized_statuses = list(
            statuses
        )

        if not normalized_statuses:
            return InvestigationStatus.NOT_EXECUTED

        for status in normalized_statuses:
            if not isinstance(
                status,
                InvestigationStatus,
            ):
                raise TypeError(
                    "All statuses must be "
                    "InvestigationStatus instances."
                )

        for candidate in self._PRIORITY:
            if candidate in normalized_statuses:
                return candidate

        return InvestigationStatus.NOT_EXECUTED

    def label(
        self,
        status: InvestigationStatus,
    ) -> str:
        if not isinstance(
            status,
            InvestigationStatus,
        ):
            raise TypeError(
                "status must be an "
                "InvestigationStatus."
            )

        labels = {
            InvestigationStatus.ALERT: (
                "Alta prioridade"
            ),
            InvestigationStatus.ATTENTION: (
                "Revisão recomendada"
            ),
            InvestigationStatus.CLEAR: (
                "Sem apontamentos"
            ),
            InvestigationStatus.NOT_EXECUTED: (
                "Análise incompleta"
            ),
        }

        return labels[status]

    def _extract_status(
        self,
        card: InvestigationCard | dict[str, Any],
    ) -> InvestigationStatus:
        if isinstance(
            card,
            InvestigationCard,
        ):
            return card.status

        if not isinstance(
            card,
            dict,
        ):
            raise TypeError(
                "Each card must be an "
                "InvestigationCard or dictionary."
            )

        raw_status = card.get(
            "status"
        )

        if isinstance(
            raw_status,
            InvestigationStatus,
        ):
            return raw_status

        if not isinstance(
            raw_status,
            str,
        ):
            raise TypeError(
                "Serialized investigation card "
                "must contain a string status."
            )

        normalized_status = (
            raw_status
            .strip()
            .lower()
        )

        try:
            return InvestigationStatus(
                normalized_status
            )
        except ValueError as error:
            raise ValueError(
                "Unknown investigation status: "
                f"{raw_status!r}."
            ) from error