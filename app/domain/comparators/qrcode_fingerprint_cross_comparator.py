from __future__ import annotations

from typing import Any

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.qrcode_fingerprint_comparator import (
    QRCodeFingerprintComparator,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)
from app.domain.services.qrcode_fingerprint_finding_builder import (
    QRCodeFingerprintFindingBuilder,
)
from app.domain.services.qrcode_fingerprint_pair_generator import (
    QRCodeFingerprintPairGenerator,
)


class QRCodeFingerprintCrossComparator(BaseComparator):
    """
    Executa a comparação cruzada dos fingerprints de QR Code
    pertencentes a documentos distintos.

    Este componente apenas orquestra:

    - geração dos pares;
    - comparação técnica dos fingerprints;
    - construção dos findings.

    Ele não interpreta o conteúdo dos QR Codes, não classifica
    correspondências e não define regras de severidade.
    """

    def __init__(
        self,
        pair_generator: QRCodeFingerprintPairGenerator | None = None,
        qrcode_comparator: QRCodeFingerprintComparator | None = None,
        finding_builder: QRCodeFingerprintFindingBuilder | None = None,
    ) -> None:
        self._pair_generator = (
            pair_generator
            or QRCodeFingerprintPairGenerator()
        )

        self._qrcode_comparator = (
            qrcode_comparator
            or QRCodeFingerprintComparator()
        )

        self._finding_builder = (
            finding_builder
            or QRCodeFingerprintFindingBuilder()
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
            comparison = self._qrcode_comparator.compare(
                pair.first_qrcode,
                pair.second_qrcode,
            )

            pair_findings = self._finding_builder.build(
                pair=pair,
                comparison=comparison,
                comparator=self.__class__.__name__,
            )

            findings.extend(pair_findings)

        return findings