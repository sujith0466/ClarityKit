"""Validation rules and boundary checks for Multi-Document Comparison (Phase 13)."""

import uuid
from collections.abc import Sequence

from app.comparison.models import (
    ComparisonNotFoundError,
    DocumentNotReadyForComparisonError,
    InvalidComparisonInputError,
)
from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository

MIN_COMPARISON_DOCS = 2
MAX_COMPARISON_DOCS = 5


class ComparisonValidator:
    """Validates multi-document comparison inputs and tenant isolation."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._doc_repo = document_repository or in_memory_document_repository

    def validate_document_ids(
        self, document_ids: Sequence[str], user_id: str
    ) -> list[Document]:
        """Validate document list bounds, deduplication, ownership, and readiness.

        Returns the validated list of Document instances.
        Raises InvalidComparisonInputError, ComparisonNotFoundError, or
        DocumentNotReadyForComparisonError.
        """
        if not document_ids:
            raise InvalidComparisonInputError(
                "At least 2 documents are required for comparison."
            )

        # Check for duplicates
        unique_ids = list(dict.fromkeys(document_ids))
        if len(unique_ids) != len(document_ids):
            raise InvalidComparisonInputError(
                "Duplicate document IDs in comparison request."
            )

        # Check bounded count
        count = len(unique_ids)
        if count < MIN_COMPARISON_DOCS:
            raise InvalidComparisonInputError(
                f"At least {MIN_COMPARISON_DOCS} distinct documents are "
                f"required (provided {count})."
            )
        if count > MAX_COMPARISON_DOCS:
            raise InvalidComparisonInputError(
                f"Maximum of {MAX_COMPARISON_DOCS} documents allowed per "
                f"comparison (provided {count})."
            )

        # Validate UUID syntax
        for doc_id in unique_ids:
            try:
                uuid.UUID(str(doc_id))
            except (ValueError, TypeError):
                raise InvalidComparisonInputError(
                    f"Invalid document UUID format: '{doc_id}'."
                )

        # Fetch documents and verify ownership (404 on non-owned or missing)
        documents: list[Document] = []
        for doc_id in unique_ids:
            doc = self._doc_repo.get_by_id(doc_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                # Return 404 to avoid leaking cross-tenant document existence
                raise ComparisonNotFoundError(f"Document '{doc_id}' not found.")
            if doc.status != DocumentStatus.READY:
                raise DocumentNotReadyForComparisonError(
                    f"Document '{doc.filename}' is currently in "
                    f"'{doc.status.value}' state and not ready for comparison."
                )
            documents.append(doc)

        return documents
