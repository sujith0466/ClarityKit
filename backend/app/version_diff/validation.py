import uuid
from typing import TYPE_CHECKING

from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.version_diff.models import (
    DocumentNotReadyForVersionDiffError,
    InvalidVersionDiffInputError,
    VersionDiffNotFoundError,
)

if TYPE_CHECKING:
    from app.extraction.models import DocumentUnderstanding


class VersionDiffValidator:
    """Validates version diff inputs, document pair boundaries, and tenant isolation."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._doc_repo = document_repository or in_memory_document_repository

    def validate_version_pair(
        self, v1_document_id: str, v2_document_id: str, user_id: str
    ) -> tuple[Document, Document]:
        """Validate that two distinct documents exist, belong to user, and are ready.

        Returns tuple of (v1_document, v2_document).
        Raises InvalidVersionDiffInputError, VersionDiffNotFoundError, or
        DocumentNotReadyForVersionDiffError.
        """
        if not v1_document_id or not v2_document_id:
            raise InvalidVersionDiffInputError(
                "Both Version 1 and Version 2 document IDs are required."
            )

        if v1_document_id == v2_document_id:
            raise InvalidVersionDiffInputError(
                "Version 1 and Version 2 document IDs must be distinct."
            )

        for doc_id, label in [
            (v1_document_id, "Version 1"),
            (v2_document_id, "Version 2"),
        ]:
            try:
                uuid.UUID(str(doc_id))
            except (ValueError, TypeError):
                raise InvalidVersionDiffInputError(
                    f"Invalid {label} document UUID format: '{doc_id}'."
                )

        # Retrieve documents and check ownership (404 for IDOR isolation)
        v1_doc = self._doc_repo.get_by_id(v1_document_id)
        if (
            v1_doc is None
            or v1_doc.user_id != user_id
            or v1_doc.status == DocumentStatus.DELETED
        ):
            raise VersionDiffNotFoundError(
                f"Version 1 document '{v1_document_id}' not found."
            )

        v2_doc = self._doc_repo.get_by_id(v2_document_id)
        if (
            v2_doc is None
            or v2_doc.user_id != user_id
            or v2_doc.status == DocumentStatus.DELETED
        ):
            raise VersionDiffNotFoundError(
                f"Version 2 document '{v2_document_id}' not found."
            )

        # Check readiness
        if v1_doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForVersionDiffError(
                f"Version 1 document '{v1_doc.filename}' is in state "
                f"'{v1_doc.status.value}' and not ready for diffing."
            )

        if v2_doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForVersionDiffError(
                f"Version 2 document '{v2_doc.filename}' is in state "
                f"'{v2_doc.status.value}' and not ready for diffing."
            )

        return v1_doc, v2_doc

    def validate_version_compatibility(
        self,
        v1_doc: Document,
        v2_doc: Document,
        v1_understanding: "DocumentUnderstanding",
        v2_understanding: "DocumentUnderstanding",
    ) -> None:
        """Ensure Version 1 and Version 2 share sufficient contractual/party identity.

        Prevents arbitrary, unrelated documents from being silently presented as
        versions of the same agreement without resorting to fragile filename heuristics.
        Raises InvalidVersionDiffInputError if documents are demonstrably unrelated.
        """
        v1_parties = [
            p.name.strip() for p in v1_understanding.parties if p.name.strip()
        ]
        v2_parties = [
            p.name.strip() for p in v2_understanding.parties if p.name.strip()
        ]

        # If both documents have identified parties, verify shared legal entities
        if v1_parties and v2_parties:
            has_common_party = self._check_party_overlap(v1_parties, v2_parties)
            if not has_common_party:
                raise InvalidVersionDiffInputError(
                    "Version 1 and Version 2 appear to be unrelated documents: "
                    "no common parties or contractual identity detected. "
                    "Use Multi-Document Comparison to compare distinct agreements."
                )

        # If both documents have structured clauses, verify category overlap
        v1_categories = {
            c.category.lower() for c in v1_understanding.clauses if c.category
        }
        v2_categories = {
            c.category.lower() for c in v2_understanding.clauses if c.category
        }
        if len(v1_understanding.clauses) >= 2 and len(v2_understanding.clauses) >= 2:
            v1_spec = {cat for cat in v1_categories if cat != "general"}
            v2_spec = {cat for cat in v2_categories if cat != "general"}
            if v1_spec and v2_spec and not (v1_spec & v2_spec):
                raise InvalidVersionDiffInputError(
                    "Version 1 and Version 2 appear to be unrelated documents: "
                    "no shared clause categories or contractual structure detected. "
                    "Use Multi-Document Comparison to compare distinct agreements."
                )

    @staticmethod
    def _check_party_overlap(parties_a: list[str], parties_b: list[str]) -> bool:
        """Check whether two party lists share at least one common entity."""

        def _normalize(name: str) -> set[str]:
            clean = "".join(
                c.lower() if c.isalnum() or c.isspace() else " " for c in name
            )
            stop_words = {
                "inc",
                "llc",
                "corp",
                "corporation",
                "ltd",
                "limited",
                "co",
                "company",
                "the",
                "and",
                "party",
                "tenant",
                "landlord",
                "borrower",
                "lender",
            }
            tokens = {t for t in clean.split() if len(t) > 1 and t not in stop_words}
            return tokens if tokens else {t for t in clean.split() if len(t) > 1}

        for pa in parties_a:
            tokens_a = _normalize(pa)
            for pb in parties_b:
                tokens_b = _normalize(pb)
                if tokens_a and tokens_b and (tokens_a & tokens_b):
                    return True
                if (
                    pa.lower() == pb.lower()
                    or pa.lower() in pb.lower()
                    or pb.lower() in pa.lower()
                ):
                    return True
        return False
