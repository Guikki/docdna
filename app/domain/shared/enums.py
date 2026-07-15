from enum import Enum


class DocumentStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"