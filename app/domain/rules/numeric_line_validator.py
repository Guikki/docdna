from app.domain.models.numeric_line_validation import (
    NumericLineType,
    NumericLineValidation,
    NumericLineValidationStatus,
)
from app.domain.models.printed_numeric_line import PrintedNumericLine


class NumericLineValidator:

    def validate(
        self,
        line: PrintedNumericLine,
    ) -> NumericLineValidation:
        content = line.normalized_content
        digit_count = len(content)

        if digit_count == 47:
            return self._validate_bank_slip(line)

        if digit_count == 48 and content.startswith("8"):
            return self._validate_collection_line(line)

        return NumericLineValidation(
            line_index=line.line_index,
            normalized_content=content,
            line_type=NumericLineType.UNKNOWN,
            status=NumericLineValidationStatus.INCONCLUSIVE,
            digit_count=digit_count,
            validation_method=None,
            valid_check_digits=0,
            total_check_digits=0,
            message=(
                "A sequência não corresponde aos formatos estruturais "
                "de 47 ou 48 dígitos atualmente reconhecidos."
            ),
        )

    def _validate_bank_slip(
        self,
        line: PrintedNumericLine,
    ) -> NumericLineValidation:
        content = line.normalized_content

        fields = [
            (content[0:9], int(content[9])),
            (content[10:20], int(content[20])),
            (content[21:31], int(content[31])),
        ]

        valid_check_digits = sum(
            self._modulo_10(field) == check_digit
            for field, check_digit in fields
        )

        status = (
            NumericLineValidationStatus.VALID
            if valid_check_digits == 3
            else NumericLineValidationStatus.INVALID
        )

        return NumericLineValidation(
            line_index=line.line_index,
            normalized_content=content,
            line_type=NumericLineType.BANK_SLIP,
            status=status,
            digit_count=47,
            validation_method="modulo_10",
            valid_check_digits=valid_check_digits,
            total_check_digits=3,
            message=(
                "Linha digitável bancária estruturalmente válida."
                if status == NumericLineValidationStatus.VALID
                else (
                    "A sequência possui 47 dígitos, mas um ou mais "
                    "dígitos verificadores dos campos são inválidos."
                )
            ),
        )

    def _validate_collection_line(
        self,
        line: PrintedNumericLine,
    ) -> NumericLineValidation:
        content = line.normalized_content
        reference_digit = content[2]

        if reference_digit in {"6", "7"}:
            validation_method = "modulo_10"
            calculator = self._modulo_10
        elif reference_digit in {"8", "9"}:
            validation_method = "modulo_11_collection"
            calculator = self._modulo_11_collection
        else:
            return NumericLineValidation(
                line_index=line.line_index,
                normalized_content=content,
                line_type=NumericLineType.COLLECTION,
                status=NumericLineValidationStatus.INCONCLUSIVE,
                digit_count=48,
                validation_method=None,
                valid_check_digits=0,
                total_check_digits=4,
                message=(
                    "A sequência possui 48 dígitos e começa com 8, "
                    "mas o identificador de referência é desconhecido."
                ),
            )

        blocks = [
            content[0:12],
            content[12:24],
            content[24:36],
            content[36:48],
        ]

        valid_check_digits = 0

        for block in blocks:
            data = block[:11]
            check_digit = int(block[11])

            if calculator(data) == check_digit:
                valid_check_digits += 1

        status = (
            NumericLineValidationStatus.VALID
            if valid_check_digits == 4
            else NumericLineValidationStatus.INVALID
        )

        return NumericLineValidation(
            line_index=line.line_index,
            normalized_content=content,
            line_type=NumericLineType.COLLECTION,
            status=status,
            digit_count=48,
            validation_method=validation_method,
            valid_check_digits=valid_check_digits,
            total_check_digits=4,
            message=(
                "Linha digitável de arrecadação estruturalmente válida."
                if status == NumericLineValidationStatus.VALID
                else (
                    "A sequência possui formato de arrecadação, mas um "
                    "ou mais dígitos verificadores são inválidos."
                )
            ),
        )

    def _modulo_10(self, content: str) -> int:
        total = 0
        multiplier = 2

        for digit_character in reversed(content):
            result = int(digit_character) * multiplier

            if result > 9:
                result = (result // 10) + (result % 10)

            total += result
            multiplier = 1 if multiplier == 2 else 2

        remainder = total % 10

        return 0 if remainder == 0 else 10 - remainder

    def _modulo_11_collection(self, content: str) -> int:
        total = 0
        multiplier = 2

        for digit_character in reversed(content):
            total += int(digit_character) * multiplier
            multiplier += 1

            if multiplier > 9:
                multiplier = 2

        remainder = total % 11

        if remainder in {0, 1}:
            return 0

        if remainder == 10:
            return 1

        return 11 - remainder