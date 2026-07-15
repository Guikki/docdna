from pydantic import BaseModel


class PdfInfoResponse(BaseModel):
    page_count: int
    title: str | None = None
    author: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    pdf_version: str | None = None
    has_text: bool
    has_images: bool