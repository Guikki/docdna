from dataclasses import dataclass


@dataclass
class DocumentText:
    content: str
    character_count: int
    pages_with_text: int