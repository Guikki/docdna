from dataclasses import dataclass


@dataclass
class PdfInfo:
    page_count: int
    title: str | None
    author: str | None
    creator: str | None
    producer: str | None
    creation_date: str | None
    modification_date: str | None
    pdf_version: str | None
    has_text: bool
    has_images: bool