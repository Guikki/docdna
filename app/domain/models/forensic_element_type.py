from enum import Enum


class ForensicElementType(str, Enum):
    DOCUMENT = "document"
    TEXT = "text"
    IMAGE = "image"
    HASH = "hash"
    BARCODE = "barcode"
    QRCODE = "qrcode"
    NUMERIC_LINE = "numeric_line"
    LOCATION = "location"
    METADATA = "metadata"
    OTHER = "other"