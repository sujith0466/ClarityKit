"""Integration tests for TimelineService and authoritative Phase 7 EvidenceValidator
(Phase 14).
"""

import uuid
from typing import Any

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.models import EvidenceValidationStatus
from app.extraction.models import (
    ExtractedDate,
    ExtractedObligation,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.timeline.models import (
    TimelineNotFoundError,
)
from app.timeline.repository import InMemoryTimelineRepository
from app.timeline.service import TimelineService


@pytest.fixture
def timeline_env() -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    tl_repo = InMemoryTimelineRepository(document_repository=doc_repo)

    service = TimelineService(
        timeline_repository=tl_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
    )

    doc_id = str(uuid.uuid4())
    doc = Document(
        document_id=doc_id,
        user_id=user_id,
        filename="Contract_2026.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="k1",
        content_hash="h1",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page_repo.save_pages(
        doc_id,
        [
            DocumentPage.create(
                document_id=doc_id,
                page_number=1,
                text="Commencement Date: January 15, 2026. Payment due within 30 days.",
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )

    extraction_repo.save_understanding(
        document_id=doc_id,
        parties=[],
        clauses=[],
        obligations=[
            ExtractedObligation.create(
                document_id=doc_id,
                obligor="Client",
                duty="Make payment",
                trigger="Commencement Date",
                deadline="30 days",
                page_start=1,
                page_end=1,
                source_span="Payment due within 30 days.",
            )
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc_id,
                date_type="effective_date",
                raw_text="January 15, 2026",
                normalized_date="2026-01-15",
                description="Commencement Date",
                page_number=1,
                source_span="January 15, 2026",
            )
        ],
        review_flags=[],
    )

    return {
        "user_id": user_id,
        "doc_id": doc_id,
        "service": service,
    }


def test_generate_and_get_timeline_evidence_validation(
    timeline_env: dict[str, Any],
) -> None:
    service = timeline_env["service"]
    user_id = timeline_env["user_id"]
    doc_id = timeline_env["doc_id"]

    timeline = service.generate_document_timeline(
        document_id=doc_id,
        user_id=user_id,
        title="Custom Timeline Title",
    )

    assert timeline.id is not None
    assert timeline.document_id == doc_id
    assert len(timeline.items) == 2

    for item in timeline.items:
        for ref in item.evidence_references:
            assert ref.validation_status == EvidenceValidationStatus.VALID
            assert ref.char_start is not None
            assert ref.char_end is not None

    # Retrieve side-effect free GET
    fetched = service.get_timeline_by_document_id(doc_id, user_id)
    assert fetched.id == timeline.id


def test_get_timeline_not_found(timeline_env: dict[str, Any]) -> None:
    service = timeline_env["service"]
    user_id = timeline_env["user_id"]

    # Before generation, get_timeline_by_document_id must raise TimelineNotFoundError
    fake_doc_id = str(uuid.uuid4())
    with pytest.raises(TimelineNotFoundError):
        service.get_timeline_by_document_id(fake_doc_id, user_id)
