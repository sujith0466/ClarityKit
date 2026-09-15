import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ExtractionMethod(str, Enum):
    NATIVE = "native"
    OCR = "ocr"


class ProcessingError(Exception):
    """Base exception for document processing errors."""

    pass


class InvalidDocumentStateError(ProcessingError):
    """Raised when a document is in an invalid state for processing."""

    pass


class CorruptDocumentError(ProcessingError):
    """Raised when the document bytes cannot be parsed as a PDF."""

    pass


class PageLimitExceededError(ProcessingError):
    """Raised when the document exceeds the maximum page limit."""

    pass


class OCRError(ProcessingError):
    """Raised when OCR extraction fails."""

    pass


@dataclass
class DocumentPage:
    id: str
    document_id: str
    page_number: int
    text: str
    extraction_method: ExtractionMethod
    char_count: int
    word_count: int
    is_empty: bool
    ocr_required: bool
    processing_duration_ms: float
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        document_id: str,
        page_number: int,
        text: str,
        extraction_method: ExtractionMethod,
        ocr_required: bool = False,
        processing_duration_ms: float = 0.0,
    ) -> "DocumentPage":
        now = datetime.now(UTC).isoformat()
        stripped = text.strip()
        char_count = len(text)
        word_count = len(stripped.split()) if stripped else 0
        is_empty = len(stripped) == 0

        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            page_number=page_number,
            text=text,
            extraction_method=extraction_method,
            char_count=char_count,
            word_count=word_count,
            is_empty=is_empty,
            ocr_required=ocr_required,
            processing_duration_ms=processing_duration_ms,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "text": self.text,
            "extraction_method": self.extraction_method.value,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "is_empty": self.is_empty,
            "ocr_required": self.ocr_required,
            "processing_duration_ms": self.processing_duration_ms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
