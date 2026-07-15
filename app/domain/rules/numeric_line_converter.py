from app.domain.models.numeric_line_validation import (
    NumericLineType,
    NumericLineValidation,
    NumericLineValidationStatus,
)


class NumericLineConverter:

    def convert_to_barcode(
        self,
        validation: NumericLineValidation,
    ) -> str | None:
        if validation.status != NumericLineValidationStatus.VALID:
            return None

        content = validation.normalized_content

        if validation.line_type == NumericLineType.BANK_SLIP:
            return self._convert_bank_slip(content)

        if validation.line_type == NumericLineType.COLLECTION:
            return self._convert_collection_line(content)

        return None

    def _convert_bank_slip(self, content: str) -> str:
        bank_and_currency = content[0:4]
        general_check_digit = content[32]
        due_date_and_value = content[33:47]

        free_field = (
            content[4:9]
            + content[10:20]
            + content[21:31]
        )

        return (
            bank_and_currency
            + general_check_digit
            + due_date_and_value
            + free_field
        )

    def _convert_collection_line(self, content: str) -> str:
        blocks_without_check_digits = [
            content[0:11],
            content[12:23],
            content[24:35],
            content[36:47],
        ]

        return "".join(blocks_without_check_digits)