from __future__ import annotations

from enum import Enum


class QRCodeMatchClassification(str, Enum):
    """
    Classificação técnica de correspondência entre dois QR Codes.

    A classificação representa apenas o grau de correspondência
    identificado pela análise dos fingerprints.

    Ela não define severidade, fraude ou evidência documental.

    Divergências específicas de conteúdo, imagem, codificação,
    versão ou correção de erro permanecem disponíveis no
    QRCodeFingerprintComparison para interpretação posterior
    pelo domínio.
    """

    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"
    EXACT = "exact"