"""Unit and service tests for Lawyer Preparation Brief generation and retrieval."""

from typing import Any

import pytest

from app.auth.models import User
from app.brief.models import (
    BriefNotFoundError,
    DocumentNotFoundError,
    DocumentNotReadyForBriefError,
)
from app.brief.repository import InMemoryBriefRepository
from app.brief.service import BriefService
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.qa.repository import InMemoryQARepository
from app.reasoning.gateway import ReasoningGateway


@pytest.fixture
def mock_brief_env() -> dict[str, Any]:
    user = User(
        user_id="user-123",
        email="user@example.com",
        password_hash="dummy",
        name="Test User",
    )

    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    qa_repo = InMemoryQARepository()
    brief_repo = InMemoryBriefRepository(document_repository=doc_repo)

    doc = Document(
        document_id="doc-brief-1",
        user_id="user-123",
        filename="Commercial_Lease.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="test_key",
        content_hash="hash-123",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page1 = DocumentPage.create(
        document_id="doc-brief-1",
        page_number=1,
        text=(
            "This Commercial Lease Agreement is entered into between "
            "Landlord Corp and Tenant LLC. Rent is $5,000."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2 = DocumentPage.create(
        document_id="doc-brief-1",
        page_number=2,
        text=(
            "Section 2. Termination. Either party may terminate with "
            "30 days notice. Restrictive covenant applies."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page1, page2])

    parties = [
        ExtractedParty.create(
            document_id=doc.id,
            name="Landlord Corp",
            role="Landlord",
            page_number=1,
            source_span="between Landlord Corp",
        ),
        ExtractedParty.create(
            document_id=doc.id,
            name="Tenant LLC",
            role="Tenant",
            page_number=1,
            source_span="and Tenant LLC",
        ),
    ]
    clauses = [
        ExtractedClause.create(
            document_id=doc.id,
            clause_identifier="Clause-2",
            title="Termination",
            category="termination",
            text="Either party may terminate with 30 days notice.",
            page_start=2,
            page_end=2,
            source_span="Either party may terminate with 30 days notice.",
        )
    ]
    obligations = [
        ExtractedObligation.create(
            document_id=doc.id,
            obligor="Tenant LLC",
            duty="shall pay rent",
            trigger=None,
            deadline="monthly",
            page_start=1,
            page_end=1,
            source_span="Rent is $5,000.",
        )
    ]
    dates = [
        ExtractedDate.create(
            document_id=doc.id,
            date_type="effective_date",
            raw_text="2026-01-01",
            normalized_date="2026-01-01",
            description="Effective date",
            page_number=1,
            source_span="entered into between",
        )
    ]
    review_flags = [
        ExtractedReviewFlag.create(
            document_id=doc.id,
            flag_type="restrictive_covenant",
            title="Restrictive Covenant",
            description="Non-compete provision identified.",
            severity="medium",
            page_start=2,
            page_end=2,
            source_span="Restrictive covenant applies.",
        )
    ]

    extraction_repo.save_understanding(
        document_id=doc.id,
        parties=parties,
        clauses=clauses,
        obligations=obligations,
        dates=dates,
        review_flags=review_flags,
    )

    service = BriefService(
        brief_repository=brief_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        qa_repository=qa_repo,
        reasoning_gateway=ReasoningGateway(),
    )

    return {
        "user": user,
        "doc": doc,
        "service": service,
        "doc_repo": doc_repo,
        "brief_repo": brief_repo,
    }


def test_generate_brief_success(mock_brief_env: dict[str, Any]) -> None:
    service: BriefService = mock_brief_env["service"]
    user: User = mock_brief_env["user"]
    doc: Document = mock_brief_env["doc"]

    brief = service.generate_brief(
        document_id=doc.id,
        user_id=user.user_id,
        title="Custom Brief Title",
    )

    assert brief.id is not None
    assert brief.document_id == doc.id
    assert brief.title == "Custom Brief Title"
    assert "parties" in brief.sections
    assert len(brief.sections["parties"].items) == 2
    assert "clauses" in brief.sections
    assert "obligations" in brief.sections
    assert "dates" in brief.sections
    assert "review_areas" in brief.sections
    assert len(brief.questions_for_lawyer) > 0
    assert len(brief.documents_to_bring) > 0
    assert brief.completeness_score > 0.5
    assert "IMPORTANT NOTICE" in brief.disclaimer


def test_get_brief_and_export_pdf(mock_brief_env: dict[str, Any]) -> None:
    service: BriefService = mock_brief_env["service"]
    user: User = mock_brief_env["user"]
    doc: Document = mock_brief_env["doc"]

    created = service.generate_brief(
        document_id=doc.id,
        user_id=user.user_id,
    )

    fetched = service.get_brief_by_document(doc.id, user.user_id)
    assert fetched is not None
    assert fetched.id == created.id

    by_id = service.get_brief_by_id(created.id, user.user_id)
    assert by_id.id == created.id

    pdf_bytes = service.export_brief_pdf(created.id, user.user_id)
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF-1.4")


def test_delete_brief(mock_brief_env: dict[str, Any]) -> None:
    service: BriefService = mock_brief_env["service"]
    user: User = mock_brief_env["user"]
    doc: Document = mock_brief_env["doc"]

    created = service.generate_brief(
        document_id=doc.id,
        user_id=user.user_id,
    )
    deleted = service.delete_brief(created.id, user.user_id)
    assert deleted is True

    with pytest.raises(BriefNotFoundError):
        service.get_brief_by_id(created.id, user.user_id)


def test_generate_brief_document_not_found(mock_brief_env: dict[str, Any]) -> None:
    service: BriefService = mock_brief_env["service"]
    user: User = mock_brief_env["user"]

    with pytest.raises(DocumentNotFoundError):
        service.generate_brief("non-existent-doc", user.user_id)


def test_generate_brief_document_not_ready(mock_brief_env: dict[str, Any]) -> None:
    service: BriefService = mock_brief_env["service"]
    user: User = mock_brief_env["user"]
    doc_repo = mock_brief_env["doc_repo"]

    pending_doc = Document(
        document_id="doc-pending",
        user_id="user-123",
        filename="Draft.pdf",
        content_type="application/pdf",
        file_size_bytes=100,
        storage_key="dummy",
        content_hash="dummy",
        status=DocumentStatus.UPLOADING,
    )
    doc_repo.save(pending_doc)

    with pytest.raises(DocumentNotReadyForBriefError):
        service.generate_brief("doc-pending", user.user_id)
