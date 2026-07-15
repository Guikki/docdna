from pydantic import BaseModel


class DocumentTextResponse(BaseModel):
    content: str
    character_count: int
    pages_with_text: int