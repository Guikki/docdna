from __future__ import annotations

from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)
from app.domain.models.qrcode_match_classification import (
    QRCodeMatchClassification,
)


class QRCodeFingerprintMatchClassifier:
    """
    Classifica o grau de correspondência técnica entre
    dois fingerprints de QR Code.

    A classificação considera separadamente:

    - o conteúdo decodificado;
    - a representação visual do QR Code.

    Regras de classificação:

    - EXACT:
      mesmo conteúdo e mesma imagem;

    - STRONG:
      mesmo conteúdo, mas imagem diferente;

    - MODERATE:
      mesma imagem, mas conteúdo diferente;

    - NONE:
      conteúdo e imagem diferentes.

    Encoding, versão, correção de erro e rotação permanecem
    disponíveis no QRCodeFingerprintComparison, mas não
    alteram diretamente a classificação principal.

    Este componente não define fraude, severidade ou
    evidência documental.
    """

    def classify(
        self,
        comparison: QRCodeFingerprintComparison,
    ) -> QRCodeMatchClassification:
        if (
            comparison.same_value
            and comparison.exact_image_match
        ):
            return QRCodeMatchClassification.EXACT

        if comparison.same_value:
            return QRCodeMatchClassification.STRONG

        if comparison.exact_image_match:
            return QRCodeMatchClassification.MODERATE

        return QRCodeMatchClassification.NONE