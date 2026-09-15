import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class DocumentStatus(str, Enum):
    """Lifecycle states for ingested legal documents."""

    UPLOADING = "UPLOADING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"
    DELETED = "DELETED"


@dataclass
class Document:
    """Core document entity representing an ingested legal document."""

    user_id: str
    filename: str
    content_type: str
    file_size_bytes: int
    storage_key: str
    content_hash: str
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: DocumentStatus = DocumentStatus.QUEUED
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def id(self) -> str:
        """Alias for document_id."""
        return self.document_id

    def to_dict(self) -> dict[str, Any]:
        """Return safe, sanitized metadata representation for API clients.

        Internal storage paths and filesystem keys are excluded.
        """
        return {
            "id": self.document_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size_bytes": self.file_size_bytes,
            "content_hash": self.content_hash,
            "status": (
                self.status.value
                if isinstance(self.status, DocumentStatus)
                else self.status
            ),
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
