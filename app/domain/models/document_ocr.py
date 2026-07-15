from dataclasses import dataclass


@dataclass
class DocumentOcr:
    content: str
    character_count: int
    pages_processed: int
    pages_with_text: int
    language: str