from __future__ import annotations

from enum import Enum


class ImageMatchClassification(str, Enum):
    """
    Classificação técnica de correspondência entre duas imagens.

    A classificação representa apenas o grau de correspondência
    identificado pelos hashes de imagem.

    Ela não define severidade, fraude ou evidência documental.
    """

    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"
    EXACT = "exact"