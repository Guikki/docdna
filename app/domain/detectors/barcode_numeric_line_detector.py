from app.domain.detectors.base_detector import BaseDetector
from app.domain.evidence.evidence import Evidence, EvidenceSeverity
from app.domain.models.analysis_context import AnalysisContext
from app.domain.models.barcode_line_comparison import (
    BarcodeLineComparison,
    BarcodeLineComparisonStatus,
)
from app.domain.models.numeric_line_validation import (
    NumericLineValidationStatus,
)
from app.domain.rules.numeric_line_converter import NumericLineConverter


class BarcodeNumericLineDetector(BaseDetector):

    def analyze(self, context: AnalysisContext) -> list[Evidence]:
        comparisons = self.compare(context)
        evidences: list[Evidence] = []

        for comparison in comparisons:
            if comparison.status == BarcodeLineComparisonStatus.MATCH:
                evidences.append(
                    Evidence(
                        code="BARCODE_LINE_MATCH",
                        title=(
                            "Código de barras e linha digitável "
                            "correspondentes"
                        ),
                        description=comparison.message,
                        severity=EvidenceSeverity.INFO,
                        detector=self.__class__.__name__,
                        confidence=1.0,
                    )
                )

            elif comparison.status == BarcodeLineComparisonStatus.MISMATCH:
                evidences.append(
                    Evidence(
                        code="BARCODE_LINE_MISMATCH",
                        title=(
                            "Divergência entre código de barras "
                            "e linha digitável"
                        ),
                        description=comparison.message,
                        severity=EvidenceSeverity.HIGH,
                        detector=self.__class__.__name__,
                        confidence=1.0,
                    )
                )

        return evidences

    def compare(
        self,
        context: AnalysisContext,
    ) -> list[BarcodeLineComparison]:
        converter = NumericLineConverter()
        comparisons: list[BarcodeLineComparison] = []

        for validation in context.numeric_line_validations:
            if validation.status != NumericLineValidationStatus.VALID:
                comparisons.append(
                    BarcodeLineComparison(
                        line_index=validation.line_index,
                        barcode_index=None,
                        line_type=validation.line_type.value,
                        printed_numeric_line=(
                            validation.normalized_content
                        ),
                        converted_barcode=None,
                        detected_barcode=None,
                        status=(
                            BarcodeLineComparisonStatus.INCONCLUSIVE
                        ),
                        message=(
                            "A sequência numérica não pôde ser "
                            "comparada porque não foi validada "
                            "estruturalmente."
                        ),
                    )
                )
                continue

            converted_barcode = converter.convert_to_barcode(
                validation
            )

            matching_barcode = self._find_compatible_barcode(
                converted_barcode=converted_barcode,
                context=context,
            )

            if matching_barcode is not None:
                comparisons.append(
                    BarcodeLineComparison(
                        line_index=validation.line_index,
                        barcode_index=matching_barcode.barcode_index,
                        line_type=validation.line_type.value,
                        printed_numeric_line=(
                            validation.normalized_content
                        ),
                        converted_barcode=converted_barcode,
                        detected_barcode=matching_barcode.content,
                        status=BarcodeLineComparisonStatus.MATCH,
                        message=(
                            "A sequência numérica impressa representa "
                            "o mesmo conteúdo lido no código de barras."
                        ),
                    )
                )
                continue

            compatible_candidates = [
                barcode
                for barcode in context.barcodes
                if self._is_payment_barcode(barcode.content)
            ]

            if compatible_candidates:
                selected_barcode = compatible_candidates[0]

                comparisons.append(
                    BarcodeLineComparison(
                        line_index=validation.line_index,
                        barcode_index=selected_barcode.barcode_index,
                        line_type=validation.line_type.value,
                        printed_numeric_line=(
                            validation.normalized_content
                        ),
                        converted_barcode=converted_barcode,
                        detected_barcode=selected_barcode.content,
                        status=BarcodeLineComparisonStatus.MISMATCH,
                        message=(
                            "A linha digitável foi validada, mas o "
                            "conteúdo equivalente não corresponde ao "
                            "código de barras lido no documento."
                        ),
                    )
                )
                continue

            comparisons.append(
                BarcodeLineComparison(
                    line_index=validation.line_index,
                    barcode_index=None,
                    line_type=validation.line_type.value,
                    printed_numeric_line=(
                        validation.normalized_content
                    ),
                    converted_barcode=converted_barcode,
                    detected_barcode=None,
                    status=BarcodeLineComparisonStatus.INCONCLUSIVE,
                    message=(
                        "A linha digitável foi validada, mas nenhum "
                        "código de barras de pagamento compatível foi "
                        "encontrado para comparação."
                    ),
                )
            )

        return comparisons

    def _find_compatible_barcode(
        self,
        converted_barcode: str | None,
        context: AnalysisContext,
    ):
        if not converted_barcode:
            return None

        for barcode in context.barcodes:
            normalized_barcode = self._normalize_digits(
                barcode.content
            )

            if normalized_barcode == converted_barcode:
                return barcode

        return None

    def _is_payment_barcode(self, content: str) -> bool:
        normalized_content = self._normalize_digits(content)

        return len(normalized_content) == 44

    def _normalize_digits(self, content: str) -> str:
        return "".join(
            character
            for character in content
            if character.isdigit()
        )