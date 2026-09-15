import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class RetrievalError(Exception):
    """Base exception for retrieval and indexing operations."""

    pass


class IndexingError(RetrievalError):
    """Raised when document chunking or vector indexing fails."""

    pass


class EmbeddingError(RetrievalError):
    """Raised when vector embedding generation fails."""

    pass


class InvalidQueryError(RetrievalError):
    """Raised when a search query violates bounds or validation rules."""

    pass


@dataclass
class RetrievalChunk:
    """Core retrieval chunk entity preserving provenance back to source pages."""

    id: str
    document_id: str
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    source_page_ids: list[str]
    char_count: int
    token_count_est: int
    content_hash: str
    embedding: list[float] | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        chunk_index: int,
        text: str,
        page_start: int,
        page_end: int,
        source_page_ids: list[str] | None = None,
        embedding: list[float] | None = None,
        chunk_id: str | None = None,
    ) -> "RetrievalChunk":
        """Factory creating a validated, hashed RetrievalChunk."""
        cleaned_text = text.strip()
        char_count = len(cleaned_text)
        # Approximate tokens as 1 token ~= 4 characters / 0.75 words
        token_count_est = max(1, round(char_count / 4))
        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).isoformat()

        return cls(
            id=chunk_id or str(uuid.uuid4()),
            document_id=document_id,
            chunk_index=chunk_index,
            text=cleaned_text,
            page_start=page_start,
            page_end=page_end,
            source_page_ids=source_page_ids or [],
            char_count=char_count,
            token_count_est=token_count_est,
            content_hash=content_hash,
            embedding=embedding,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self, include_embedding: bool = False) -> dict[str, Any]:
        """Convert chunk entity to safe JSON dictionary."""
        data: dict[str, Any] = {
            "id": self.id,
            "chunk_id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_page_ids": self.source_page_ids,
            "char_count": self.char_count,
            "token_count_est": self.token_count_est,
            "content_hash": self.content_hash,
            "has_embedding": self.embedding is not None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_embedding and self.embedding is not None:
            data["embedding"] = self.embedding
        return data


@dataclass
class RetrievalResult:
    """Ranked search result with explicit provenance and similarity score."""

    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    similarity: float
    char_count: int
    word_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert retrieval result to safe dictionary for API responses."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "similarity": round(self.similarity, 4),
            "char_count": self.char_count,
            "word_count": self.word_count,
        }
