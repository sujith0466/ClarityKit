import threading
from abc import ABC, abstractmethod

from app.documents.models import Document, DocumentStatus


class DocumentRepository(ABC):
    """Abstract document metadata repository interface."""

    @abstractmethod
    def save(self, document: Document) -> Document:
        """Save a new document or update an existing document."""
        pass

    @abstractmethod
    def get_by_id(self, document_id: str) -> Document | None:
        """Retrieve a document by its unique document_id."""
        pass

    @abstractmethod
    def list_by_user(
        self, user_id: str, include_deleted: bool = False
    ) -> list[Document]:
        """List all documents owned by a specific user."""
        pass

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """Mark document as deleted or remove from repository."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored documents (for testing)."""
        pass


class InMemoryDocumentRepository(DocumentRepository):
    """Thread-safe in-memory document repository."""

    def __init__(self) -> None:
        self._documents_by_id: dict[str, Document] = {}
        self._lock = threading.RLock()

    def save(self, document: Document) -> Document:
        with self._lock:
            self._documents_by_id[document.document_id] = document
            return document

    def get_by_id(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents_by_id.get(document_id)

    def list_by_user(
        self, user_id: str, include_deleted: bool = False
    ) -> list[Document]:
        with self._lock:
            docs = [
                doc for doc in self._documents_by_id.values() if doc.user_id == user_id
            ]
            if not include_deleted:
                docs = [doc for doc in docs if doc.status != DocumentStatus.DELETED]
            # Sort newest first
            return sorted(docs, key=lambda d: d.created_at, reverse=True)

    def delete(self, document_id: str) -> bool:
        with self._lock:
            if document_id in self._documents_by_id:
                # Mark status as DELETED
                self._documents_by_id[document_id].status = DocumentStatus.DELETED
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._documents_by_id.clear()


# Default singleton repository
_default_document_repository: DocumentRepository = InMemoryDocumentRepository()


def get_document_repository() -> DocumentRepository:
    """Get active document repository instance."""
    return _default_document_repository


def set_document_repository(repository: DocumentRepository) -> None:
    """Set active document repository instance (for testing/customization)."""
    global _default_document_repository
    _default_document_repository = repository
