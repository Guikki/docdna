from pydantic import BaseModel


class DocumentOcrResponse(BaseModel):
    content: str
    character_count: int
    pages_processed: int
    pages_with_text: int
    language: str