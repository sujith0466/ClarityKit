"""Comparison Service for multi-document analysis and evidence validation."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from app.comparison.matcher import ComparisonMatcher
from app.comparison.models import (
    ComparisonDocumentRef,
    ComparisonFinding,
    ComparisonNotFoundError,
    ComparisonSummary,
    DifferenceClassification,
    DocumentComparison,
    DocumentEvidenceRef,
)
from app.comparison.repository import (
    ComparisonRepository,
    in_memory_comparison_repository,
)
from app.comparison.validation import ComparisonValidator
from app.documents.repository import (
    DocumentRepository,
    in_memory_document_repository,
)
from app.evidence.models import EvidenceValidationStatus
from app.evidence.resolver import SourceSpanResolver
from app.extraction.models import DocumentUnderstanding
from app.extraction.repository import (
    ExtractionRepository,
    in_memory_extraction_repository,
)
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)
from app.trust.models import SafetyStatus, TrustTier

logger = logging.getLogger(__name__)


class ComparisonService:
    """Orchestrates multi-document comparison and evidence validation."""

    def __init__(
        self,
        comparison_repository: ComparisonRepository | None = None,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
    ) -> None:
        self._comp_repo = comparison_repository or in_memory_comparison_repository
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or in_memory_extraction_repository
        self._validator = ComparisonValidator(self._doc_repo)

    def generate_comparison(
        self,
        document_ids: Sequence[str],
        user_id: str,
        title: str | None = None,
    ) -> DocumentComparison:
        """Perform cross-document comparison with deterministic matching."""
        # 1. Validate inputs, count, ownership, and readiness
        docs = self._validator.validate_document_ids(document_ids, user_id)

        # 2. Retrieve page texts and extractions for each document
        page_texts_by_doc: dict[str, dict[int, str]] = {}
        extractions_by_doc: dict[str, DocumentUnderstanding] = {}
        doc_refs: list[ComparisonDocumentRef] = []
        doc_titles: dict[str, str] = {}

        for doc in docs:
            doc_id = doc.id
            title_str = doc.filename or f"Document {doc_id[:8]}"
            doc_titles[doc_id] = title_str

            pages = self._page_repo.get_pages_by_document(doc_id)
            page_texts_by_doc[doc_id] = {p.page_number: p.text for p in pages}

            understanding = self._extraction_repo.get_understanding_by_document(doc_id)
            extractions_by_doc[doc_id] = understanding or DocumentUnderstanding(
                document_id=doc_id
            )

            doc_refs.append(
                ComparisonDocumentRef(
                    document_id=doc_id,
                    title=title_str,
                    filename=doc.filename,
                    page_count=len(pages) if pages else 1,
                )
            )

        # 3. Perform deterministic cross-document comparison
        raw_findings = ComparisonMatcher.compare_documents(
            doc_ids=[d.id for d in docs],
            doc_titles=doc_titles,
            extractions=extractions_by_doc,
        )

        # 4. Cross-document evidence validation using Phase 7 SourceSpanResolver
        validated_findings: list[ComparisonFinding] = []
        for finding in raw_findings:
            validated_refs: list[DocumentEvidenceRef] = []
            all_refs_valid = True

            for ref in finding.evidence_references:
                doc_page_texts = page_texts_by_doc.get(ref.document_id, {})
                if not doc_page_texts:
                    ref.validation_status = EvidenceValidationStatus.INVALID
                    all_refs_valid = False
                    validated_refs.append(ref)
                    continue

                res = SourceSpanResolver.resolve(
                    page_texts=doc_page_texts,
                    page_start=ref.page_start,
                    page_end=ref.page_end,
                    source_span=ref.source_span,
                )
                ref.validation_status = res.status
                ref.char_start = res.char_start
                ref.char_end = res.char_end
                if res.source_text:
                    ref.exact_quote = res.source_text
                if res.status != EvidenceValidationStatus.VALID:
                    all_refs_valid = False

                validated_refs.append(ref)

            finding.evidence_references = validated_refs

            # 5. Enforce NO EVIDENCE -> NO DOCUMENT-SPECIFIC CLAIM
            if not all_refs_valid:
                # If any document-specific evidence fails, mark as UNRESOLVED
                finding.classification = DifferenceClassification.UNRESOLVED
                finding.trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                finding.safety_status = SafetyStatus.REVIEW_REQUIRED
                finding.description += (
                    " [Notice: One or more evidence citations could not be "
                    "mechanically verified against the source text.]"
                )
            else:
                # Assign Phase 8 Trust & Safety statuses based on classification
                if finding.classification in (
                    DifferenceClassification.MATCH,
                    DifferenceClassification.DIFFERENT,
                    DifferenceClassification.PRESENT_IN_ONE_ONLY,
                ):
                    finding.trust_tier = TrustTier.DOCUMENT_FACT
                    finding.safety_status = SafetyStatus.SAFE
                elif (
                    finding.classification
                    == DifferenceClassification.POTENTIAL_INCONSISTENCY
                ):
                    finding.trust_tier = TrustTier.DOCUMENT_FACT
                    finding.safety_status = SafetyStatus.REVIEW_REQUIRED
                else:
                    finding.trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    finding.safety_status = SafetyStatus.LIMITED

            validated_findings.append(finding)

        # 6. Compute summary
        summary = ComparisonSummary.compute(validated_findings)

        # 7. Construct and persist comparison record
        default_title = (
            title or f"Comparison: {' vs '.join([d.title for d in doc_refs[:2]])}"
        )
        comparison = DocumentComparison(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=default_title,
            document_ids=[d.id for d in docs],
            documents=doc_refs,
            findings=validated_findings,
            summary=summary,
        )

        saved = self._comp_repo.save_comparison(comparison, user_id)
        return saved

    def get_comparison_by_id(
        self, comparison_id: str, user_id: str
    ) -> DocumentComparison:
        """Retrieve a comparison by ID enforcing tenant isolation."""
        comparison = self._comp_repo.get_comparison_by_id(comparison_id, user_id)
        if comparison is None:
            raise ComparisonNotFoundError(
                f"Comparison '{comparison_id}' was not found."
            )
        return comparison

    def list_comparisons_for_user(self, user_id: str) -> list[DocumentComparison]:
        """List all comparisons for the authenticated user."""
        return self._comp_repo.list_comparisons_for_user(user_id)

    def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        """Delete a comparison by ID enforcing tenant isolation."""
        deleted = self._comp_repo.delete_comparison(comparison_id, user_id)
        if not deleted:
            raise ComparisonNotFoundError(
                f"Comparison '{comparison_id}' was not found."
            )
        return deleted

    def delete_comparisons_for_document(self, document_id: str, user_id: str) -> int:
        """Delete all comparisons referencing a deleted document."""
        return self._comp_repo.delete_comparisons_for_document(document_id, user_id)


# Default service instance
_global_comparison_service: ComparisonService | None = None


def get_comparison_service() -> ComparisonService:
    """Retrieve singleton ComparisonService instance."""
    global _global_comparison_service
    if _global_comparison_service is None:
        _global_comparison_service = ComparisonService()
    return _global_comparison_service
