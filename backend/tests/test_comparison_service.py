"""Integration tests for ComparisonService and Phase 7 evidence (Phase 13)."""

import uuid
from typing import Any

import pytest

from app.comparison.models import (
    ComparisonNotFoundError,
    DifferenceClassification,
    InvalidComparisonInputError,
)
from app.comparison.repository import InMemoryComparisonRepository
from app.comparison.service import ComparisonService
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.models import EvidenceValidationStatus
from app.extraction.models import (
    ExtractedDate,
    ExtractedParty,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.trust.models import SafetyStatus, TrustTier


@pytest.fixture
def mock_repos() -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository()
    comp_repo = InMemoryComparisonRepository(document_repository=doc_repo)

    # Create 2 documents
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    doc1 = Document(
        document_id=doc1_id,
        user_id=user_id,
        filename="offer_letter.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        storage_key="k1",
        content_hash="h1",
        status=DocumentStatus.READY,
    )
    doc2 = Document(
        document_id=doc2_id,
        user_id=user_id,
        filename="employment_contract.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="k2",
        content_hash="h2",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc1)
    doc_repo.save(doc2)

    # Pages
    page1 = DocumentPage.create(
        document_id=doc1_id,
        page_number=1,
        text=(
            "This Offer Letter is made by Acme Corp to John Smith. "
            "Employment begins October 1, 2026."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2 = DocumentPage.create(
        document_id=doc2_id,
        page_number=1,
        text=(
            "Employment Agreement between Acme Corp and John Smith. "
            "Start Date shall be October 15, 2026."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc1_id, [page1])
    page_repo.save_pages(doc2_id, [page2])

    # Extractions
    parties1 = [
        ExtractedParty.create(
            document_id=doc1_id,
            name="Acme Corp",
            role="Employer",
            page_number=1,
            source_span="Acme Corp",
        ),
        ExtractedParty.create(
            document_id=doc1_id,
            name="John Smith",
            role="Employee",
            page_number=1,
            source_span="John Smith",
        ),
    ]
    dates1 = [
        ExtractedDate.create(
            document_id=doc1_id,
            raw_text="October 1, 2026",
            normalized_date="2026-10-01",
            date_type="effective_date",
            description="Start Date",
            page_number=1,
            source_span="October 1, 2026",
        )
    ]
    extraction_repo.save_understanding(
        document_id=doc1_id,
        parties=parties1,
        clauses=[],
        obligations=[],
        dates=dates1,
        review_flags=[],
    )

    parties2 = [
        ExtractedParty.create(
            document_id=doc2_id,
            name="Acme Corp",
            role="Employer",
            page_number=1,
            source_span="Acme Corp",
        ),
        ExtractedParty.create(
            document_id=doc2_id,
            name="John Smith",
            role="Employee",
            page_number=1,
            source_span="John Smith",
        ),
    ]
    dates2 = [
        ExtractedDate.create(
            document_id=doc2_id,
            raw_text="October 15, 2026",
            normalized_date="2026-10-15",
            date_type="effective_date",
            description="Start Date",
            page_number=1,
            source_span="October 15, 2026",
        )
    ]
    extraction_repo.save_understanding(
        document_id=doc2_id,
        parties=parties2,
        clauses=[],
        obligations=[],
        dates=dates2,
        review_flags=[],
    )

    service = ComparisonService(
        comparison_repository=comp_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
    )

    return {
        "user_id": user_id,
        "doc1_id": doc1_id,
        "doc2_id": doc2_id,
        "service": service,
        "comp_repo": comp_repo,
    }


def test_generate_comparison_success_with_evidence_validation(
    mock_repos: dict[str, Any],
) -> None:
    """Test generating a comparison and verifying mechanical evidence resolution."""
    service = mock_repos["service"]
    user_id = mock_repos["user_id"]
    doc1_id = mock_repos["doc1_id"]
    doc2_id = mock_repos["doc2_id"]

    comparison = service.generate_comparison(
        document_ids=[doc1_id, doc2_id],
        user_id=user_id,
        title="Offer vs Contract Comparison",
    )

    assert comparison.id is not None
    assert comparison.user_id == user_id
    assert len(comparison.documents) == 2
    assert comparison.summary.total_findings >= 3

    # Check evidence validation status on findings
    for finding in comparison.findings:
        for ref in finding.evidence_references:
            assert ref.validation_status == EvidenceValidationStatus.VALID
            assert ref.char_start is not None
            assert ref.char_end is not None

    # Check date inconsistency finding
    date_finding = next(
        f
        for f in comparison.findings
        if f.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
    )
    assert date_finding.trust_tier == TrustTier.DOCUMENT_FACT
    assert date_finding.safety_status == SafetyStatus.REVIEW_REQUIRED


def test_comparison_retrieval_and_deletion(mock_repos: dict[str, Any]) -> None:
    """Test retrieving and deleting persisted comparisons."""
    service = mock_repos["service"]
    user_id = mock_repos["user_id"]
    doc1_id = mock_repos["doc1_id"]
    doc2_id = mock_repos["doc2_id"]

    comp = service.generate_comparison(
        document_ids=[doc1_id, doc2_id],
        user_id=user_id,
    )

    fetched = service.get_comparison_by_id(comp.id, user_id)
    assert fetched.id == comp.id

    listed = service.list_comparisons_for_user(user_id)
    assert len(listed) == 1

    deleted = service.delete_comparison(comp.id, user_id)
    assert deleted is True

    with pytest.raises(ComparisonNotFoundError):
        service.get_comparison_by_id(comp.id, user_id)


def test_comparison_invalid_bounds(mock_repos: dict[str, Any]) -> None:
    """Test rejection when document count is less than 2 or exceeds 5."""
    service = mock_repos["service"]
    user_id = mock_repos["user_id"]
    doc1_id = mock_repos["doc1_id"]

    # Less than 2 documents
    with pytest.raises(InvalidComparisonInputError):
        service.generate_comparison(document_ids=[doc1_id], user_id=user_id)

    # Exceeding 5 documents
    fake_ids = [str(uuid.uuid4()) for _ in range(6)]
    with pytest.raises(InvalidComparisonInputError):
        service.generate_comparison(document_ids=fake_ids, user_id=user_id)
