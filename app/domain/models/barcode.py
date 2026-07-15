from dataclasses import dataclass


@dataclass
class Barcode:
    barcode_index: int
    page_number: int
    format: str
    content: str