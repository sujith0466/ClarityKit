import uuid
from typing import Any

from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository, get_document_repository
from app.documents.validation import validate_file_upload
from app.storage.interface import StorageService
from app.storage.local import get_storage_service


class DocumentServiceError(Exception):
    """Base exception for document service errors."""

    pass


class DocumentService:
    """Business logic service for document ingestion, retrieval, and deletion."""

    def __init__(
        self,
        repository: DocumentRepository | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self._repository = repository or get_document_repository()
        self._storage = storage or get_storage_service()

    def upload_document(
        self,
        user_id: str,
        file_obj: Any,
        max_size_bytes: int = 20 * 1024 * 1024,
    ) -> Document:
        """Securely ingest a user uploaded PDF document.

        1. Validate file (type, signature, size, filename).
        2. Generate IDs and secure storage key.
        3. Save file to storage.
        4. Save metadata record (QUEUED).
        5. Atomically rollback storage if metadata persistence fails.
        """
        content, sanitized_filename, content_type, content_hash = validate_file_upload(
            file_obj, max_size_bytes=max_size_bytes
        )

        document_id = str(uuid.uuid4())
        storage_key = self._storage.generate_storage_key(
            user_id=user_id,
            document_id=document_id,
            extension=".pdf",
        )

        # Write to storage
        self._storage.save(storage_key, content)

        try:
            document = Document(
                document_id=document_id,
                user_id=user_id,
                filename=sanitized_filename,
                content_type=content_type,
                file_size_bytes=len(content),
                storage_key=storage_key,
                content_hash=content_hash,
                status=DocumentStatus.QUEUED,
            )
            saved_doc = self._repository.save(document)
            return saved_doc
        except Exception as e:
            # Atomic cleanup: remove orphaned stored file on persistence failure
            self._storage.delete(storage_key)
            raise DocumentServiceError(
                f"Failed to persist document metadata: {e}"
            ) from e

    def get_document(self, user_id: str, document_id: str) -> Document | None:
        """Retrieve document metadata by ID, strictly verifying user ownership."""
        doc = self._repository.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return None
        return doc

    def list_documents(self, user_id: str) -> list[Document]:
        """List all active documents owned by the authenticated user."""
        return self._repository.list_by_user(user_id, include_deleted=False)

    def delete_document(self, user_id: str, document_id: str) -> bool:
        """Delete document file and mark metadata as deleted.

        Strictly verifies user ownership.
        """
        doc = self._repository.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return False

        # Remove from storage
        self._storage.delete(doc.storage_key)

        # Mark deleted in repository
        return self._repository.delete(document_id)
