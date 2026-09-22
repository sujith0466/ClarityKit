"""Service layer orchestrating Deadline & Obligation Timeline generation (Phase 14)."""

import logging
import uuid
from datetime import UTC, datetime

from app.documents.models import Document, DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.evidence.validators import EvidenceValidator
from app.extraction.models import DocumentUnderstanding
from app.extraction.repository import (
    ExtractionRepository,
    get_extraction_repository,
)
from app.processing.repository import PageRepository, in_memory_page_repository
from app.timeline.models import (
    DocumentNotReadyForTimelineError,
    DocumentTimeline,
    InvalidTimelineInputError,
    TimelineItem,
    TimelineNotFoundError,
    TimelineSummary,
)
from app.timeline.repository import (
    TimelineRepository,
    in_memory_timeline_repository,
)
from app.timeline.timeline_engine import TimelineEngine
from app.trust.models import SafetyStatus, TrustTier

logger = logging.getLogger(__name__)


class TimelineService:
    """Coordinates timeline extraction, Phase 7 evidence validation, and persistence."""

    def __init__(
        self,
        timeline_repository: TimelineRepository | None = None,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
    ) -> None:
        self._tl_repo = timeline_repository or in_memory_timeline_repository
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or get_extraction_repository()

    def generate_document_timeline(
        self,
        document_id: str,
        user_id: str,
        title: str | None = None,
    ) -> DocumentTimeline:
        """Generate, validate, and persist a chronological timeline for a document."""
        doc = self._validate_document(document_id, user_id)
        page_texts = self._load_page_texts(doc.id)
        understanding = self._load_understanding(doc.id, user_id)

        # 1. Synthesize timeline items deterministically
        raw_items = TimelineEngine.build_timeline(
            document_id=doc.id,
            document_title=doc.filename,
            understanding=understanding,
        )

        # 2. Authoritative Phase 7 Evidence Validation & Trust/Safety Integration
        validated_items: list[TimelineItem] = []
        for item in raw_items:
            all_valid = True
            for ref in item.evidence_references:
                if not ref.source_span or not page_texts:
                    ref.validation_status = EvidenceValidationStatus.INVALID
                    all_valid = False
                    continue

                claim_ref = EvidenceReference(
                    document_id=doc.id,
                    page_start=ref.page_start,
                    page_end=ref.page_end,
                    source_span=ref.source_span,
                    section=ref.section,
                )
                claim = Claim.create(
                    document_id=doc.id,
                    claim_text=ref.exact_quote or ref.source_span,
                    claim_type=ClaimType.DATE,
                    evidence=claim_ref,
                )

                # Route through authoritative Phase 7 EvidenceValidator
                validated_claim = EvidenceValidator.validate_claim(claim, page_texts)

                if validated_claim.evidence:
                    ref.validation_status = validated_claim.evidence.validation_status
                    ref.char_start = validated_claim.evidence.char_start
                    ref.char_end = validated_claim.evidence.char_end
                    if validated_claim.evidence.source_text:
                        ref.exact_quote = validated_claim.evidence.source_text

                if ref.validation_status != EvidenceValidationStatus.VALID:
                    all_valid = False

            if not all_valid:
                item.trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                item.safety_status = SafetyStatus.REVIEW_REQUIRED
                item.notes += (
                    " [Evidence could not be mechanically verified "
                    "against document text.]"
                )

            validated_items.append(item)

        # 3. Summary computation
        summary = TimelineSummary.from_items(validated_items)

        # 4. Construct aggregate DocumentTimeline
        tl_id = str(uuid.uuid4())
        tl_title = (
            title.strip() if title and title.strip() else f"Timeline: {doc.filename}"
        )
        now_str = datetime.now(UTC).isoformat()

        timeline = DocumentTimeline(
            id=tl_id,
            user_id=user_id,
            document_id=doc.id,
            document_title=doc.filename,
            title=tl_title,
            items=validated_items,
            summary=summary,
            created_at=now_str,
            updated_at=now_str,
        )

        return self._tl_repo.save_timeline(timeline, user_id)

    def get_timeline_by_id(self, timeline_id: str, user_id: str) -> DocumentTimeline:
        """Retrieve an existing timeline by its timeline ID."""
        tl = self._tl_repo.get_timeline_by_id(timeline_id, user_id)
        if tl is None:
            raise TimelineNotFoundError(
                f"Timeline '{timeline_id}' not found or unauthorized."
            )
        return tl

    def get_timeline_by_document_id(
        self, document_id: str, user_id: str
    ) -> DocumentTimeline:
        """Retrieve an existing persisted timeline for a document (side-effect free)."""
        # Ensure document exists and user has access
        self._validate_document(document_id, user_id)

        tl = self._tl_repo.get_timeline_by_document_id(document_id, user_id)
        if tl is None:
            raise TimelineNotFoundError(
                f"No timeline generated yet for document '{document_id}'."
            )
        return tl

    def list_timelines_for_user(self, user_id: str) -> list[DocumentTimeline]:
        """List all timelines for the authenticated user."""
        return self._tl_repo.list_timelines_for_user(user_id)

    def delete_timeline(self, timeline_id: str, user_id: str) -> bool:
        """Delete a timeline record."""
        return self._tl_repo.delete_timeline(timeline_id, user_id)

    def delete_timelines_for_document(self, document_id: str, user_id: str) -> int:
        """Cascade delete all timelines associated with a specific document."""
        return self._tl_repo.delete_timelines_for_document(document_id, user_id)

    def _validate_document(self, document_id: str, user_id: str) -> Document:
        if not document_id:
            raise InvalidTimelineInputError("Document ID is required.")

        try:
            uuid.UUID(str(document_id))
        except (ValueError, TypeError):
            raise InvalidTimelineInputError(
                f"Invalid document UUID format: '{document_id}'."
            )

        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise TimelineNotFoundError(f"Document '{document_id}' not found.")

        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForTimelineError(
                f"Document '{doc.filename}' is in state '{doc.status.value}' "
                f"and not ready for timeline generation."
            )

        return doc

    def _load_page_texts(self, document_id: str) -> dict[int, str]:
        pages = self._page_repo.get_pages_by_document(document_id)
        return {p.page_number: p.text for p in pages}

    def _load_understanding(
        self, document_id: str, user_id: str
    ) -> DocumentUnderstanding:
        understanding = self._extraction_repo.get_understanding_by_document(
            document_id, user_id
        )
        if understanding is None:
            return DocumentUnderstanding(document_id=document_id)
        return understanding
