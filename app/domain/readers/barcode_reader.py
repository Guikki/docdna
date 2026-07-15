from io import BytesIO

import pymupdf
import zxingcpp
from PIL import Image

from app.domain.models.barcode import Barcode
from app.domain.readers.base_reader import BaseReader


class BarcodeReader(BaseReader):

    def read(self, source: str) -> list[Barcode]:
        detected_barcodes: list[Barcode] = []

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(document, start=1):
                page_image = self._render_page(page)

                results = zxingcpp.read_barcodes(page_image)

                for result in results:
                    content = result.text.strip()

                    if not content:
                        continue

                    detected_barcodes.append(
                        Barcode(
                            barcode_index=len(detected_barcodes) + 1,
                            page_number=page_number,
                            format=str(result.format),
                            content=content,
                        )
                    )

        return detected_barcodes

    def _render_page(self, page: pymupdf.Page) -> Image.Image:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(3, 3),
            alpha=False,
        )

        image_bytes = pixmap.tobytes("png")

        return Image.open(BytesIO(image_bytes)).convert("RGB")