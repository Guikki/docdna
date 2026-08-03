from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)


@dataclass(frozen=True, slots=True)
class LogoFingerprintComparison(
    ImageFingerprintComparison
):
    """
    Representa o resultado técnico da comparação entre
    dois fingerprints de logo.

    Além das métricas visuais herdadas da comparação de imagens,
    informa se os nomes das empresas associados às logos
    também coincidem.

    O campo same_company_name possui três estados:

    - True: os dois nomes foram informados e são iguais;
    - False: os dois nomes foram informados e são diferentes;
    - None: não foi possível comparar os nomes.
    """

    same_company_name: bool | None = None

    def __post_init__(self) -> None:
        ImageFingerprintComparison.__post_init__(
            self
        )

    @property
    def has_company_name_comparison(self) -> bool:
        """
        Indica se havia nomes de empresa suficientes
        para realizar a comparação.
        """

        return self.same_company_name is not None

    @property
    def is_same_company_logo(self) -> bool:
        """
        Indica que a comparação de nomes confirmou
        que as duas logos pertencem à mesma empresa.
        """

        return self.same_company_name is True