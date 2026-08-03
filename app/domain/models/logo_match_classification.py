from __future__ import annotations

from enum import Enum


class LogoMatchClassification(str, Enum):
    """
    Classificação técnica de correspondência entre dois logos.

    A classificação representa o grau de correspondência
    identificado pela análise visual dos fingerprints.

    Ela não define severidade, fraude ou evidência documental.
    A eventual divergência entre nomes de empresas permanece
    disponível no LogoFingerprintComparison para interpretação
    posterior pelo domínio.
    """

    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"
    EXACT = "exact"