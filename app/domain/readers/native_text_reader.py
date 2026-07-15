import pymupdf

from app.domain.models.document_text import DocumentText
from app.domain.readers.base_reader import BaseReader


class NativeTextReader(BaseReader):

    def read(self, source: str) -> DocumentText:
        pages_text: list[str] = []
        pages_with_text = 0

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()

                if not page_text:
                    continue

                pages_with_text += 1
                pages_text.append(
                    f"--- Página {page_number} ---\n{page_text}"
                )

        content = "\n\n".join(pages_text)

        return DocumentText(
            content=content,
            character_count=len(content),
            pages_with_text=pages_with_text,
        )