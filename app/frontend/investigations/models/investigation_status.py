from __future__ import annotations

from enum import Enum


class InvestigationStatus(str, Enum):
    """
    Representa o estado visual de uma etapa investigativa.

    Este status serve exclusivamente para apresentação no frontend.
    Não traz atestado de autenticidade documental, confirmação de fraude, classificação pericial,
    decisão jurídica ou risco global do documento.

    O valor resume somente os resultados produzidos pelos
    verificadores executados naquela etapa.
    """

    CLEAR = "clear"
    ATTENTION = "attention"
    ALERT = "alert"
    NOT_EXECUTED = "not_executed"