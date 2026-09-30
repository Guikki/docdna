from enum import Enum


class ForensicDataLayer(str, Enum):
    SOURCE = "source"
    EXTRACTED = "extracted"
    DERIVED = "derived"
    CLASSIFIED = "classified"
    ANALYTICAL = "analytical"