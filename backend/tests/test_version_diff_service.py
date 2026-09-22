"""Integration tests for VersionDiffService and authoritative Phase 7 EvidenceValidator
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
    ExtractedParty,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.trust.models import SafetyStatus, TrustTier
from app.version_diff.models import (
    InvalidVersionDiffInputError,
    VersionDiffClassification,
)
from app.version_diff.repository import InMemoryVersionDiffRepository
from app.version_diff.service import VersionDiffService


@pytest.fixture
def diff_env() -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    diff_repo = InMemoryVersionDiffRepository(document_repository=doc_repo)

    service = VersionDiffService(
        version_diff_repository=diff_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
    )

    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    doc1 = Document(
        document_id=doc1_id,
        user_id=user_id,
        filename="Lease_Draft_v1.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="k1",
        content_hash="h1",
        status=DocumentStatus.READY,
    )
    doc2 = Document(
        document_id=doc2_id,
        user_id=user_id,
        filename="Lease_Draft_v2.pdf",
        content_type="application/pdf",
        file_size_bytes=2500,
        storage_key="k2",
        content_hash="h2",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc1)
    doc_repo.save(doc2)

    page_repo.save_pages(
        doc1_id,
        [
            DocumentPage.create(
                document_id=doc1_id,
                page_number=1,
                text=(
                    "Tenant: Acme Corp. Effective Date: January 1, 2026. "
                    "Notice: 30 days."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )
    page_repo.save_pages(
        doc2_id,
        [
            DocumentPage.create(
                document_id=doc2_id,
                page_number=1,
                text=(
                    "Tenant: Acme Corp. Effective Date: March 1, 2026. Notice: 60 days."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )

    extraction_repo.save_understanding(
        document_id=doc1_id,
        parties=[
            ExtractedParty.create(
                document_id=doc1_id,
                name="Acme Corp",
                role="Tenant",
                page_number=1,
                source_span="Acme Corp",
            )
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc1_id,
                date_type="effective_date",
                raw_text="January 1, 2026",
                normalized_date="2026-01-01",
                description="Effective Date",
                page_number=1,
                source_span="January 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc1_id,
                obligor="Acme Corp",
                duty="give notice",
                trigger="notice",
                deadline="30 days",
                page_start=1,
                page_end=1,
                source_span="30 days",
            )
        ],
        clauses=[],
        review_flags=[],
    )

    extraction_repo.save_understanding(
        document_id=doc2_id,
        parties=[
            ExtractedParty.create(
                document_id=doc2_id,
                name="Acme Corp",
                role="Tenant",
                page_number=1,
                source_span="Acme Corp",
            )
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc2_id,
                date_type="effective_date",
                raw_text="March 1, 2026",
                normalized_date="2026-03-01",
                description="Effective Date",
                page_number=1,
                source_span="March 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc2_id,
                obligor="Acme Corp",
                duty="give notice",
                trigger="notice",
                deadline="60 days",
                page_start=1,
                page_end=1,
                source_span="60 days",
            )
        ],
        clauses=[],
        review_flags=[],
    )

    return {
        "user_id": user_id,
        "doc1_id": doc1_id,
        "doc2_id": doc2_id,
        "service": service,
    }


def test_version_diff_service_evidence_validation(diff_env: dict[str, Any]) -> None:
    service = diff_env["service"]
    user_id = diff_env["user_id"]
    doc1_id = diff_env["doc1_id"]
    doc2_id = diff_env["doc2_id"]

    diff = service.generate_version_diff(
        v1_document_id=doc1_id,
        v2_document_id=doc2_id,
        user_id=user_id,
        title="Lease v1 vs v2",
    )

    assert diff.id is not None
    assert len(diff.findings) == 3

    # All citations must pass authoritative Phase 7 mechanical validation
    for f in diff.findings:
        for ref in f.v1_evidence + f.v2_evidence:
            assert ref.validation_status == EvidenceValidationStatus.VALID
            assert ref.char_start is not None
            assert ref.char_end is not None

    date_finding = next(f for f in diff.findings if "Date" in f.title)
    assert date_finding.classification == VersionDiffClassification.MODIFIED
    assert date_finding.trust_tier == TrustTier.DOCUMENT_FACT
    assert date_finding.safety_status == SafetyStatus.SAFE


def test_version_diff_service_boundary_rejection(diff_env: dict[str, Any]) -> None:
    service = diff_env["service"]
    user_id = diff_env["user_id"]
    doc1_id = diff_env["doc1_id"]

    # Identical document IDs rejected
    with pytest.raises(InvalidVersionDiffInputError):
        service.generate_version_diff(
            v1_document_id=doc1_id,
            v2_document_id=doc1_id,
            user_id=user_id,
        )


def test_version_diff_rejects_unrelated_documents(diff_env: dict[str, Any]) -> None:
    service = diff_env["service"]
    user_id = diff_env["user_id"]
    doc1_id = diff_env["doc1_id"]
    doc_repo = service._doc_repo
    page_repo = service._page_repo
    extraction_repo = service._extraction_repo

    unrelated_id = str(uuid.uuid4())
    unrelated_doc = Document(
        document_id=unrelated_id,
        user_id=user_id,
        filename="Unrelated_Employment_Agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=3000,
        storage_key="k_unrelated",
        content_hash="h_unrelated",
        status=DocumentStatus.READY,
    )
    doc_repo.save(unrelated_doc)

    page_repo.save_pages(
        unrelated_id,
        [
            DocumentPage.create(
                document_id=unrelated_id,
                page_number=1,
                text="Employer: Wayne Enterprises. Employee: Bruce Wayne.",
                extraction_method=ExtractionMethod.NATIVE,
            )
        ],
    )

    extraction_repo.save_understanding(
        document_id=unrelated_id,
        parties=[
            ExtractedParty.create(
                document_id=unrelated_id,
                name="Wayne Enterprises",
                role="Employer",
                page_number=1,
                source_span="Employer: Wayne Enterprises",
            ),
            ExtractedParty.create(
                document_id=unrelated_id,
                name="Bruce Wayne",
                role="Employee",
                page_number=1,
                source_span="Employee: Bruce Wayne",
            ),
        ],
        dates=[],
        obligations=[],
        clauses=[],
        review_flags=[],
    )

    # Diffing Acme Lease (doc1) with Wayne Employment Agreement must be rejected
    with pytest.raises(InvalidVersionDiffInputError, match="unrelated documents"):
        service.generate_version_diff(
            v1_document_id=doc1_id,
            v2_document_id=unrelated_id,
            user_id=user_id,
        )
