from app.domain.detectors.base_detector import BaseDetector
from app.domain.evidence.evidence import Evidence, EvidenceSeverity
from app.domain.models.analysis_context import AnalysisContext


class BarcodePresenceDetector(BaseDetector):

    def analyze(self, context: AnalysisContext) -> list[Evidence]:
        barcode_count = len(context.barcodes)

        if barcode_count == 0:
            return [
                Evidence(
                    code="BARCODE_NOT_FOUND",
                    title="Código de barras não identificado",
                    description=(
                        "Nenhum código de barras pôde ser lido "
                        "automaticamente no documento."
                    ),
                    severity=EvidenceSeverity.INFO,
                    detector=self.__class__.__name__,
                    confidence=1.0,
                )
            ]

        return [
            Evidence(
                code="BARCODE_FOUND",
                title="Código de barras identificado",
                description=(
                    f"Foram encontrados {barcode_count} código(s) "
                    "de barras no documento."
                ),
                severity=EvidenceSeverity.INFO,
                detector=self.__class__.__name__,
                confidence=1.0,
            )
        ]