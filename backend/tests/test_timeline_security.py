"""Security tests for Deadline & Obligation Timeline (Phase 14)."""

import uuid
from typing import Any

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    ExtractedDate,
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
def tl_sec_env() -> dict[str, Any]:
    user_a = "user-alice"
    user_b = "user-bob"

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

    doc_a_id = str(uuid.uuid4())
    doc_b_id = str(uuid.uuid4())

    doc_a = Document(
        document_id=doc_a_id,
        user_id=user_a,
        filename="alice_contract.pdf",
        content_type="application/pdf",
        file_size_bytes=1000,
        storage_key="k1",
        content_hash="h1",
        status=DocumentStatus.READY,
    )
    doc_b = Document(
        document_id=doc_b_id,
        user_id=user_b,
        filename="bob_contract.pdf",
        content_type="application/pdf",
        file_size_bytes=1000,
        storage_key="k2",
        content_hash="h2",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc_a)
    doc_repo.save(doc_b)

    page_repo.save_pages(
        doc_a_id,
        [
            DocumentPage.create(
                document_id=doc_a_id,
                page_number=1,
                text="Jan 1, 2026",
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )
    page_repo.save_pages(
        doc_b_id,
        [
            DocumentPage.create(
                document_id=doc_b_id,
                page_number=1,
                text="Feb 1, 2026",
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )

    extraction_repo.save_understanding(
        document_id=doc_a_id,
        parties=[],
        dates=[
            ExtractedDate.create(
                document_id=doc_a_id,
                date_type="effective_date",
                raw_text="Jan 1, 2026",
                normalized_date="2026-01-01",
                description="Effective Date",
                page_number=1,
                source_span="Jan 1, 2026",
            )
        ],
        clauses=[],
        obligations=[],
        review_flags=[],
    )

    return {
        "user_a": user_a,
        "user_b": user_b,
        "doc_a_id": doc_a_id,
        "doc_b_id": doc_b_id,
        "service": service,
        "doc_repo": doc_repo,
    }


def test_cross_tenant_timeline_generation_rejection(
    tl_sec_env: dict[str, Any],
) -> None:
    service = tl_sec_env["service"]
    user_a = tl_sec_env["user_a"]
    doc_b_id = tl_sec_env["doc_b_id"]

    # Alice cannot generate timeline for Bob's doc (404)
    with pytest.raises(TimelineNotFoundError):
        service.generate_document_timeline(doc_b_id, user_a)


def test_cross_tenant_timeline_retrieval_rejection(
    tl_sec_env: dict[str, Any],
) -> None:
    service = tl_sec_env["service"]
    user_a = tl_sec_env["user_a"]
    user_b = tl_sec_env["user_b"]
    doc_a_id = tl_sec_env["doc_a_id"]

    timeline = service.generate_document_timeline(doc_a_id, user_a)

    # Bob cannot retrieve Alice's timeline (404)
    with pytest.raises(TimelineNotFoundError):
        service.get_timeline_by_id(timeline.id, user_b)

    with pytest.raises(TimelineNotFoundError):
        service.get_timeline_by_document_id(doc_a_id, user_b)

    assert len(service.list_timelines_for_user(user_b)) == 0


def test_timeline_deletion_safety(tl_sec_env: dict[str, Any]) -> None:
    service = tl_sec_env["service"]
    user_a = tl_sec_env["user_a"]
    doc_a_id = tl_sec_env["doc_a_id"]
    doc_repo = tl_sec_env["doc_repo"]

    timeline = service.generate_document_timeline(doc_a_id, user_a)

    # Delete doc
    doc_a = doc_repo.get_by_id(doc_a_id)
    assert doc_a is not None
    doc_a.status = DocumentStatus.DELETED
    doc_repo.save(doc_a)

    # Invalidation on read returns 404
    with pytest.raises(TimelineNotFoundError):
        service.get_timeline_by_id(timeline.id, user_a)
