from dataclasses import dataclass


@dataclass
class DocumentImage:
    image_index: int
    page_number: int
    xref: int
    filename: str
    saved_path: str
    extension: str
    width: int
    height: int
    size_bytes: int