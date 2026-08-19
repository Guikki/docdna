from __future__ import annotations

from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from app.config.settings import settings
from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.concealment.models.visual_concealment_location import (
    VisualConcealmentLocation,
)


class VisualConcealmentEvidenceBuilder:
    """
    Produz evidência visual para achados de ocultação textual.

    Diferentemente do localizador de Prompt Injection, este builder não
    executa matching textual nem utiliza OCR para descobrir a posição.
    A localização já vem do BoundingBox nativo preservado pelo
    TextConcealmentFinding.
    """

    RENDER_SCALE = 2.0
    HIGHLIGHT_PADDING = 16
    HIGHLIGHT_WIDTH = 6

    def build(
        self,
        *,
        pdf_path: str,
        findings: tuple[TextConcealmentFinding, ...]
        | list[TextConcealmentFinding],
    ) -> list[VisualConcealmentLocation]:
        if not isinstance(pdf_path, str):
            raise TypeError("pdf_path must be a string.")

        if not isinstance(findings, (tuple, list)):
            raise TypeError("findings must be a tuple or list.")

        source_path = Path(pdf_path)
        if not source_path.exists():
            raise FileNotFoundError(f"PDF source not found: {pdf_path}")

        output_dir = (
            settings.EXTRACTED_DIR
            / source_path.stem
            / "visual-concealment-evidence"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        result: list[VisualConcealmentLocation] = []

        for finding_index, finding in enumerate(findings, start=1):
            if not isinstance(finding, TextConcealmentFinding):
                raise TypeError(
                    "findings must contain only "
                    "TextConcealmentFinding instances."
                )

            result.append(
                self._build_location(
                    pdf_path=pdf_path,
                    finding=finding,
                    finding_index=finding_index,
                    output_dir=output_dir,
                )
            )

        return result

    def _build_location(
        self,
        *,
        pdf_path: str,
        finding: TextConcealmentFinding,
        finding_index: int,
        output_dir: Path,
    ) -> VisualConcealmentLocation:
        box = finding.bounding_box

        left = float(box.left)
        top = float(box.top)
        width = float(box.width)
        height = float(box.height)

        if width <= 0.0 or height <= 0.0:
            raise ValueError(
                "TextConcealmentFinding bounding box "
                "must have positive width and height."
            )

        source_image_path, annotated_image_path = self._render_annotated_page(
            pdf_path=pdf_path,
            page_number=finding.page_number,
            finding_index=finding_index,
            left=left,
            top=top,
            width=width,
            height=height,
            output_dir=output_dir,
        )

        return VisualConcealmentLocation(
            finding_index=finding_index,
            finding_code=finding.code,
            detector=finding.detector,
            page_number=finding.page_number,
            matched_content=finding.text,
            left=left,
            top=top,
            width=width,
            height=height,
            confidence=finding.confidence,
            source_image_path=str(source_image_path),
            annotated_image_path=str(annotated_image_path),
            located=True,
            message=(
                "O trecho associado ao achado de ocultação visual foi "
                "localizado diretamente pelas coordenadas nativas do PDF."
            ),
            font_name=finding.font_name,
            font_size=finding.font_size,
            font_color_hex=finding.font_color_hex,
        )

    def _render_annotated_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
        finding_index: int,
        left: float,
        top: float,
        width: float,
        height: float,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        if page_number < 1:
            raise ValueError("page_number must be greater than or equal to 1.")

        matrix = pymupdf.Matrix(self.RENDER_SCALE, self.RENDER_SCALE)

        with pymupdf.open(pdf_path) as document:
            if page_number > len(document):
                raise ValueError("page_number exceeds PDF page count.")

            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )

        source_image_path = output_dir / f"page_{page_number}_source.png"
        annotated_image_path = output_dir / (
            f"page_{page_number}_concealment_{finding_index}_annotated.png"
        )

        image.save(source_image_path)

        annotated_image = image.copy()
        draw = ImageDraw.Draw(annotated_image)

        render_left = left * self.RENDER_SCALE
        render_top = top * self.RENDER_SCALE
        render_width = width * self.RENDER_SCALE
        render_height = height * self.RENDER_SCALE

        padding = self.HIGHLIGHT_PADDING

        x1 = max(render_left - padding, 0.0)
        y1 = max(render_top - padding, 0.0)
        x2 = min(
            render_left + render_width + padding,
            float(annotated_image.width),
        )
        y2 = min(
            render_top + render_height + padding,
            float(annotated_image.height),
        )

        draw.rectangle(
            (x1, y1, x2, y2),
            outline="red",
            width=self.HIGHLIGHT_WIDTH,
        )

        annotated_image.save(annotated_image_path)

        return source_image_path, annotated_image_path