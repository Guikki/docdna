import pymupdf

from app.domain.models.pdf_info import PdfInfo
from app.domain.readers.base_reader import BaseReader


class PdfReader(BaseReader):

    def read(self, source: str) -> PdfInfo:
        with pymupdf.open(source) as document:
            metadata = document.metadata or {}

            has_text = False
            has_images = False

            for page in document:
                if page.get_text("text").strip():
                    has_text = True

                if page.get_images(full=True):
                    has_images = True

            return PdfInfo(
                page_count=document.page_count,
                title=metadata.get("title") or None,
                author=metadata.get("author") or None,
                creator=metadata.get("creator") or None,
                producer=metadata.get("producer") or None,
                creation_date=metadata.get("creationDate") or None,
                modification_date=metadata.get("modDate") or None,
                pdf_version=None,
                has_text=has_text,
                has_images=has_images,
            )