from pathlib import Path

import pymupdf

from app.config.settings import settings
from app.domain.models.document_image import DocumentImage
from app.domain.readers.base_reader import BaseReader


class ImageReader(BaseReader):

    def read(self, source: str) -> list[DocumentImage]:
        source_path = Path(source)
        extraction_dir = settings.EXTRACTED_DIR / source_path.stem / "images"
        extraction_dir.mkdir(parents=True, exist_ok=True)

        extracted_images: list[DocumentImage] = []
        processed_xrefs: set[int] = set()

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(document, start=1):
                page_images = page.get_images(full=True)

                for image_data in page_images:
                    xref = image_data[0]

                    if xref in processed_xrefs:
                        continue

                    extracted_image = document.extract_image(xref)

                    if not extracted_image:
                        continue

                    image_bytes = extracted_image["image"]
                    extension = extracted_image.get("ext", "bin")
                    width = extracted_image.get("width", 0)
                    height = extracted_image.get("height", 0)

                    image_index = len(extracted_images) + 1
                    filename = f"image_{image_index}_xref_{xref}.{extension}"
                    saved_path = extraction_dir / filename

                    saved_path.write_bytes(image_bytes)

                    extracted_images.append(
                        DocumentImage(
                            image_index=image_index,
                            page_number=page_number,
                            xref=xref,
                            filename=filename,
                            saved_path=str(saved_path),
                            extension=extension,
                            width=width,
                            height=height,
                            size_bytes=len(image_bytes),
                        )
                    )

                    processed_xrefs.add(xref)

        return extracted_images