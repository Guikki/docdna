import re
from datetime import datetime, timedelta, timezone
from typing import Any


BRASILIA_TIMEZONE = timezone(
    timedelta(hours=-3),
    name="Horário de Brasília",
)


class AnalysisViewBuilder:

    def build(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        pdf_info = analysis_data["pdf_info"]
        native_text = analysis_data["native_text"]
        ocr = analysis_data["ocr"]
        images = analysis_data["images"]
        barcodes = analysis_data["barcodes"]
        printed_numeric_lines = analysis_data["printed_numeric_lines"]

        numeric_line_validations = analysis_data[
            "numeric_line_validations"
        ]

        barcode_line_comparisons = analysis_data[
            "barcode_line_comparisons"
        ]

        numeric_line_locations = analysis_data[
            "numeric_line_locations"
        ]

        evidences = analysis_data["evidences"]

        formatted_evidences = [
            {
                "code": evidence.code,
                "title": evidence.title,
                "description": evidence.description,
                "severity": evidence.severity.value,
                "detector": evidence.detector,
                "confidence": evidence.confidence,
            }
            for evidence in evidences
        ]

        formatted_numeric_line_validations = [
            {
                "line_index": validation.line_index,
                "normalized_content": validation.normalized_content,
                "line_type": validation.line_type.value,
                "line_type_label": self._translate_numeric_line_type(
                    validation.line_type.value
                ),
                "status": validation.status.value,
                "status_label": self._translate_validation_status(
                    validation.status.value
                ),
                "validation_method": validation.validation_method,
                "validation_method_label":
                    self._translate_validation_method(
                        validation.validation_method
                    ),
                "valid_check_digits": validation.valid_check_digits,
                "total_check_digits": validation.total_check_digits,
                "message": validation.message,
            }
            for validation in numeric_line_validations
        ]

        formatted_barcode_line_comparisons = [
            {
                "line_index": comparison.line_index,
                "barcode_index": comparison.barcode_index,
                "line_type": comparison.line_type,
                "line_type_label": self._translate_numeric_line_type(
                    comparison.line_type
                ),
                "printed_numeric_line": (
                    comparison.printed_numeric_line
                ),
                "converted_barcode": comparison.converted_barcode,
                "detected_barcode": comparison.detected_barcode,
                "status": comparison.status.value,
                "status_label": self._translate_comparison_status(
                    comparison.status.value
                ),
                "message": comparison.message,
            }
            for comparison in barcode_line_comparisons
        ]

        barcode_formats = sorted(
            {
                barcode.format
                for barcode in barcodes
                if barcode.format
            }
        )

        barcode_pages = sorted(
            {
                barcode.page_number
                for barcode in barcodes
            }
        )

        numeric_line_sources = sorted(
            {
                line.source
                for line in printed_numeric_lines
            }
        )

        formatted_numeric_line_locations = [
            {
                "line_index": location.line_index,
                "page_number": location.page_number,
                "matched_content": location.matched_content,
                "left": location.left,
                "top": location.top,
                "width": location.width,
                "height": location.height,
                "confidence": location.confidence,
                "confidence_label": self._format_confidence(
                    location.confidence
                ),
                "source_image_url": self._build_extracted_file_url(
                    location.source_image_path
                ),
                "annotated_image_url": self._build_extracted_file_url(
                    location.annotated_image_path
                ),
                "located": location.located,
                "message": location.message,
            }
            for location in numeric_line_locations
        ]

        return {
            "id": analysis_data["id"],
            "filename": analysis_data["original_filename"],

            "uploaded_at": self._format_datetime(
                analysis_data["uploaded_at"]
            ),

            "size_bytes": analysis_data["size_bytes"],

            "formatted_size": self._format_file_size(
                analysis_data["size_bytes"]
            ),

            "sha256": analysis_data["sha256"],

            # Informações estruturais do PDF
            "page_count": pdf_info.page_count,
            "pdf_title": pdf_info.title or "Não informado",
            "pdf_author": pdf_info.author or "Não informado",
            "pdf_creator": pdf_info.creator or "Não informado",
            "pdf_producer": pdf_info.producer or "Não informado",

            "pdf_creation_date": self._format_pdf_datetime(
                pdf_info.creation_date
            ),

            "pdf_modification_date": self._format_pdf_datetime(
                pdf_info.modification_date
            ),

            "pdf_creation_date_raw": (
                pdf_info.creation_date or "Não informada"
            ),

            "pdf_modification_date_raw": (
                pdf_info.modification_date or "Não informada"
            ),

            "pdf_version": (
                pdf_info.pdf_version or "Não identificada"
            ),

            "has_native_text": pdf_info.has_text,
            "has_images": pdf_info.has_images,

            # Texto nativo
            "native_text_message": self._build_native_text_message(
                native_text.pages_with_text
            ),

            "native_text_content": native_text.content,

            "native_text_character_count": (
                native_text.character_count
            ),

            "native_text_pages": native_text.pages_with_text,

            # OCR
            "ocr_message": self._build_ocr_message(
                ocr.pages_processed,
                ocr.pages_with_text,
            ),

            "ocr_content": ocr.content,
            "ocr_character_count": ocr.character_count,
            "ocr_pages_processed": ocr.pages_processed,
            "ocr_pages_with_text": ocr.pages_with_text,
            "ocr_language": ocr.language,

            # Imagens
            "images": images,
            "image_count": len(images),

            "image_message": self._build_image_message(
                len(images)
            ),

            # Códigos
            "barcodes": barcodes,
            "barcode_count": len(barcodes),

            "barcode_message": self._build_barcode_message(
                len(barcodes)
            ),

            "barcode_formats": (
                ", ".join(barcode_formats)
                if barcode_formats
                else "Nenhum"
            ),

            "barcode_pages": (
                ", ".join(
                    str(page)
                    for page in barcode_pages
                )
                if barcode_pages
                else "Nenhuma"
            ),

            # Sequências numéricas
            "printed_numeric_lines": printed_numeric_lines,

            "printed_numeric_line_count": len(
                printed_numeric_lines
            ),

            "printed_numeric_line_message":
                self._build_printed_numeric_line_message(
                    len(printed_numeric_lines)
                ),

            "printed_numeric_line_sources": (
                ", ".join(
                    self._translate_source(source)
                    for source in numeric_line_sources
                )
                if numeric_line_sources
                else "Nenhuma"
            ),

            "printed_numeric_digit_total": sum(
                line.digit_count
                for line in printed_numeric_lines
            ),

            # Validação estrutural
            "numeric_line_validations":
                formatted_numeric_line_validations,

            "valid_numeric_line_count": sum(
                validation.status.value == "valid"
                for validation in numeric_line_validations
            ),

            "invalid_numeric_line_count": sum(
                validation.status.value == "invalid"
                for validation in numeric_line_validations
            ),

            "inconclusive_numeric_line_count": sum(
                validation.status.value == "inconclusive"
                for validation in numeric_line_validations
            ),

            # Comparação entre linha digitável e código de barras
            "barcode_line_comparisons":
                formatted_barcode_line_comparisons,

            "barcode_line_match_count": sum(
                comparison.status.value == "match"
                for comparison in barcode_line_comparisons
            ),

            "barcode_line_mismatch_count": sum(
                comparison.status.value == "mismatch"
                for comparison in barcode_line_comparisons
            ),

            "barcode_line_inconclusive_count": sum(
                comparison.status.value == "inconclusive"
                for comparison in barcode_line_comparisons
            ),

            # Localização visual das sequências
            "numeric_line_locations":
                formatted_numeric_line_locations,

            "located_numeric_line_count": sum(
                location.located
                for location in numeric_line_locations
            ),

            "unlocated_numeric_line_count": sum(
                not location.located
                for location in numeric_line_locations
            ),

            # Evidências
            "evidences": formatted_evidences,
            "evidence_count": len(formatted_evidences),
        }


    def _format_datetime(self, value: datetime) -> str:
        return value.strftime("%d/%m/%Y às %H:%M:%S")

    def _format_file_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} bytes"

        size_kb = size_bytes / 1024

        if size_kb < 1024:
            return f"{size_kb:.2f} KB"

        size_mb = size_kb / 1024
        return f"{size_mb:.2f} MB"

    def _translate_source(self, source: str) -> str:
        if source == "ocr":
            return "OCR"

        if source == "native_text":
            return "Texto nativo"

        return source

    def _build_native_text_message(
        self,
        pages_with_text: int,
    ) -> str:
        if pages_with_text == 0:
            return "Não foi encontrada camada de texto nativo."

        if pages_with_text == 1:
            return (
                "Foi encontrada camada de texto nativo "
                "em 1 página."
            )

        return (
            "Foi encontrada camada de texto nativo em "
            f"{pages_with_text} páginas."
        )

    def _build_ocr_message(
        self,
        pages_processed: int,
        pages_with_text: int,
    ) -> str:
        if pages_with_text == 0:
            return (
                f"O OCR processou {pages_processed} página(s), "
                "mas não identificou texto legível."
            )

        return (
            f"O OCR processou {pages_processed} página(s) "
            f"e encontrou texto em {pages_with_text} página(s)."
        )

    def _build_image_message(
        self,
        image_count: int,
    ) -> str:
        if image_count == 0:
            return "Nenhuma imagem interna foi extraída."

        if image_count == 1:
            return "Foi extraída 1 imagem interna."

        return (
            f"Foram extraídas {image_count} imagens internas."
        )

    def _build_barcode_message(
        self,
        barcode_count: int,
    ) -> str:
        if barcode_count == 0:
            return "Nenhum código foi lido automaticamente."

        if barcode_count == 1:
            return "Foi encontrado 1 código no documento."

        return (
            f"Foram encontrados {barcode_count} códigos "
            "no documento."
        )

    def _build_printed_numeric_line_message(
        self,
        line_count: int,
    ) -> str:
        if line_count == 0:
            return (
                "Nenhuma sequência numérica compatível com "
                "uma possível linha digitável foi localizada."
            )

        if line_count == 1:
            return (
                "Foi localizada 1 sequência numérica que pode "
                "corresponder à linha digitável. O resultado da "
                "validação estrutural está disponível abaixo."
            )

        return (
            f"Foram localizadas {line_count} sequências numéricas "
            "que podem corresponder a linhas digitáveis. Os resultados "
            "das validações estruturais estão disponíveis abaixo."
        )

    def _translate_numeric_line_type(
        self,
        line_type: str,
    ) -> str:
        labels = {
            "bank_slip": "Boleto bancário",
            "collection": "Arrecadação ou concessionária",
            "unknown": "Formato não reconhecido",
        }

        return labels.get(line_type, line_type)

    def _translate_validation_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "valid": "Válida",
            "invalid": "Inválida",
            "inconclusive": "Inconclusiva",
        }

        return labels.get(status, status)

    def _translate_comparison_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "match": "Correspondência confirmada",
            "mismatch": "Divergência identificada",
            "inconclusive": "Comparação inconclusiva",
        }

        return labels.get(status, status)

    def _translate_validation_method(
        self,
        validation_method: str | None,
    ) -> str:
        labels = {
            "modulo_10": "Módulo 10",
            "modulo_11_collection": "Módulo 11",
            None: "Não aplicável",
        }

        return labels.get(
            validation_method,
            str(validation_method),
        )

    def _format_pdf_datetime(
        self,
        value: str | None,
    ) -> str:
        if not value:
            return "Não informada"

        pattern = re.compile(
            r"^D:"
            r"(?P<year>\d{4})"
            r"(?P<month>\d{2})?"
            r"(?P<day>\d{2})?"
            r"(?P<hour>\d{2})?"
            r"(?P<minute>\d{2})?"
            r"(?P<second>\d{2})?"
            r"(?P<offset_sign>[+\-Z])?"
            r"(?P<offset_hour>\d{2})?"
            r"'?"
            r"(?P<offset_minute>\d{2})?"
            r"'?"
            r"$"
        )

        match = pattern.match(value.strip())

        if not match:
            return value

        values = match.groupdict()

        try:
            year = int(values["year"])
            month = int(values["month"] or 1)
            day = int(values["day"] or 1)
            hour = int(values["hour"] or 0)
            minute = int(values["minute"] or 0)
            second = int(values["second"] or 0)

            source_timezone = self._build_pdf_timezone(
                sign=values["offset_sign"],
                hour=values["offset_hour"],
                minute=values["offset_minute"],
            )

            pdf_datetime = datetime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
                tzinfo=source_timezone,
            )

            brasilia_datetime = pdf_datetime.astimezone(
                BRASILIA_TIMEZONE
            )

            formatted_datetime = brasilia_datetime.strftime(
                "%d/%m/%Y às %H:%M:%S"
            )

            return (
                f"{formatted_datetime} — "
                "horário de Brasília (UTC−3)"
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return value

    def _build_pdf_timezone(
        self,
        sign: str | None,
        hour: str | None,
        minute: str | None,
    ) -> timezone:
        if sign == "Z":
            return timezone.utc

        if sign in {"+", "-"}:
            offset_hours = int(hour or 0)
            offset_minutes = int(minute or 0)

            offset = timedelta(
                hours=offset_hours,
                minutes=offset_minutes,
            )

            if sign == "-":
                offset = -offset

            return timezone(offset)

        return BRASILIA_TIMEZONE

    def _format_confidence(
            self,
            confidence: float | None,
    ) -> str:
        if confidence is None:
            return "Não informada"

        return f"{confidence:.1f}%"
    def _format_confidence(
        self,
        confidence: float | None,
    ) -> str:
        if confidence is None:
            return "Não informada"

        return f"{confidence:.1f}%"

    def _build_extracted_file_url(
        self,
        file_path: str | None,
    ) -> str | None:
        if not file_path:
            return None

        normalized_path = file_path.replace("\\", "/")
        marker = "/extracted/"

        if marker not in normalized_path:
            return None

        relative_path = normalized_path.split(
            marker,
            maxsplit=1,
        )[1]

        return f"/extracted/{relative_path}"