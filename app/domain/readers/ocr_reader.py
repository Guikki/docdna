from io import BytesIO
from typing import Any

import pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output

from app.config.settings import settings
from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.ocr_result import OcrResult
from app.domain.models.ocr_text_box import OcrTextBox
from app.domain.readers.base_reader import BaseReader


class OcrReader(BaseReader):

    def __init__(self, language: str = "por") -> None:
        self.language = language

        pytesseract.pytesseract.tesseract_cmd = str(
            settings.TESSERACT_CMD
        )

    def read(self, source: str) -> OcrResult:
        pages_text: list[str] = []
        text_boxes: list[OcrTextBox] = []

        pages_processed = 0
        pages_with_text = 0

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                pages_processed += 1

                page_image = self._render_page(page)

                ocr_data = pytesseract.image_to_data(
                    page_image,
                    lang=self.language,
                    output_type=Output.DICT,
                )

                page_boxes = self._build_text_boxes(
                    ocr_data=ocr_data,
                    page_number=page_number,
                )

                page_text = self._build_page_text(
                    ocr_data=ocr_data,
                )

                text_boxes.extend(page_boxes)

                if not page_text:
                    continue

                pages_with_text += 1

                pages_text.append(
                    f"--- Página {page_number} ---\n"
                    f"{page_text}"
                )

        content = "\n\n".join(pages_text)

        document_ocr = DocumentOcr(
            content=content,
            character_count=len(content),
            pages_processed=pages_processed,
            pages_with_text=pages_with_text,
            language=self.language,
        )

        return OcrResult(
            document_ocr=document_ocr,
            text_boxes=text_boxes,
        )

    def _render_page(
        self,
        page: pymupdf.Page,
    ) -> Image.Image:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2),
            alpha=False,
        )

        image_bytes = BytesIO(
            pixmap.tobytes("png")
        )

        image = Image.open(image_bytes)

        return image.convert("RGB")

    def _build_text_boxes(
        self,
        ocr_data: dict[str, list[Any]],
        page_number: int,
    ) -> list[OcrTextBox]:
        boxes: list[OcrTextBox] = []

        total_items = len(
            ocr_data.get("text", [])
        )

        for index in range(total_items):
            text = str(
                ocr_data["text"][index]
            ).strip()

            if not text:
                continue

            confidence = self._parse_confidence(
                ocr_data["conf"][index]
            )

            if confidence < 0:
                continue

            boxes.append(
                OcrTextBox(
                    page_number=page_number,
                    text=text,
                    confidence=confidence,
                    left=int(
                        ocr_data["left"][index]
                    ),
                    top=int(
                        ocr_data["top"][index]
                    ),
                    width=int(
                        ocr_data["width"][index]
                    ),
                    height=int(
                        ocr_data["height"][index]
                    ),
                )
            )

        return boxes

    def _build_page_text(
        self,
        ocr_data: dict[str, list[Any]],
    ) -> str:
        lines: dict[
            tuple[int, int, int],
            list[tuple[int, str]],
        ] = {}

        total_items = len(
            ocr_data.get("text", [])
        )

        for index in range(total_items):
            text = str(
                ocr_data["text"][index]
            ).strip()

            if not text:
                continue

            confidence = self._parse_confidence(
                ocr_data["conf"][index]
            )

            if confidence < 0:
                continue

            line_key = (
                int(ocr_data["block_num"][index]),
                int(ocr_data["par_num"][index]),
                int(ocr_data["line_num"][index]),
            )

            word_number = int(
                ocr_data["word_num"][index]
            )

            lines.setdefault(
                line_key,
                [],
            ).append(
                (
                    word_number,
                    text,
                )
            )

        page_lines: list[str] = []

        for line_key in sorted(lines):
            ordered_words = sorted(
                lines[line_key],
                key=lambda item: item[0],
            )

            line_text = " ".join(
                word
                for _, word in ordered_words
            ).strip()

            if line_text:
                page_lines.append(line_text)

        return "\n".join(page_lines)

    def _parse_confidence(
        self,
        raw_confidence: Any,
    ) -> float:
        try:
            return float(raw_confidence)

        except (
            TypeError,
            ValueError,
        ):
            return -1.0