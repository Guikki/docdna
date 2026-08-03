from __future__ import annotations

from typing import Any

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.logo_fingerprint_comparator import (
    LogoFingerprintComparator,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)
from app.domain.services.logo_fingerprint_finding_builder import (
    LogoFingerprintFindingBuilder,
)
from app.domain.services.logo_fingerprint_pair_generator import (
    LogoFingerprintPairGenerator,
)


class LogoFingerprintCrossComparator(BaseComparator):
    """
    Executa a comparação cruzada dos fingerprints de logo
    pertencentes a documentos distintos.

    Este componente apenas orquestra:

    - geração dos pares;
    - comparação técnica dos fingerprints;
    - construção dos findings.

    Ele não calcula hashes, não classifica similaridade e não
    define regras de severidade.
    """

    def __init__(
        self,
        pair_generator: LogoFingerprintPairGenerator | None = None,
        logo_comparator: LogoFingerprintComparator | None = None,
        finding_builder: LogoFingerprintFindingBuilder | None = None,
    ) -> None:
        self._pair_generator = (
            pair_generator
            or LogoFingerprintPairGenerator()
        )

        self._logo_comparator = (
            logo_comparator
            or LogoFingerprintComparator()
        )

        self._finding_builder = (
            finding_builder
            or LogoFingerprintFindingBuilder()
        )

    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        pairs = self._pair_generator.generate(
            analyses
        )

        findings: list[CrossValidationFinding] = []

        for pair in pairs:
            comparison = self._logo_comparator.compare(
                pair.first_logo,
                pair.second_logo,
            )

            pair_findings = self._finding_builder.build(
                pair=pair,
                comparison=comparison,
                comparator=self.__class__.__name__,
            )

            findings.extend(pair_findings)

        return findings