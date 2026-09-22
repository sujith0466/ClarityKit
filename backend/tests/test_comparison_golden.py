"""Golden evaluation test suite for Multi-Document Comparison (Phase 13)."""

import uuid
from typing import Any

import pytest

from app.comparison.models import (
    ComparisonCategory,
    DifferenceClassification,
)
from app.comparison.repository import InMemoryComparisonRepository
from app.comparison.service import ComparisonService
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.models import EvidenceValidationStatus
from app.extraction.models import (
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.trust.models import TrustTier


@pytest.fixture
def golden_env() -> dict[str, Any]:
    user_id = "golden-user-123"
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository()
    comp_repo = InMemoryComparisonRepository(document_repository=doc_repo)

    # Document 1: Primary Lease Agreement
    doc1_id = str(uuid.uuid4())
    doc1 = Document(
        document_id=doc1_id,
        user_id=user_id,
        filename="Commercial_Lease_Agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=4096,
        storage_key="lease_1",
        content_hash="hash_lease",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc1)

    # Document 2: Lease Addendum
    doc2_id = str(uuid.uuid4())
    doc2 = Document(
        document_id=doc2_id,
        user_id=user_id,
        filename="Lease_Addendum_2026.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="lease_addendum",
        content_hash="hash_addendum",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc2)

    # Document Pages
    page_repo.save_pages(
        doc1_id,
        [
            DocumentPage.create(
                document_id=doc1_id,
                page_number=1,
                text=(
                    "Landlord: Apex Properties LLC. Tenant: Nexus Tech Inc. "
                    "Lease commences January 1, 2026. Monthly rent is $5,000."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            ),
            DocumentPage.create(
                document_id=doc1_id,
                page_number=2,
                text=(
                    "Tenant must provide 30 days notice prior to lease expiration. "
                    "Landlord shall provide maintenance."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            ),
        ],
    )
    page_repo.save_pages(
        doc2_id,
        [
            DocumentPage.create(
                document_id=doc2_id,
                page_number=1,
                text=(
                    "Addendum between Apex Properties LLC and Nexus Tech Inc. "
                    "Lease commencement date modified to February 1, 2026."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            ),
            DocumentPage.create(
                document_id=doc2_id,
                page_number=2,
                text=(
                    "Tenant shall provide 60 days written notice for renewal. "
                    "Parking space allocated in Section B."
                ),
                extraction_method=ExtractionMethod.NATIVE,
            ),
        ],
    )

    # Extractions for Doc 1
    extraction_repo.save_understanding(
        document_id=doc1_id,
        parties=[
            ExtractedParty.create(
                document_id=doc1_id,
                name="Apex Properties LLC",
                role="Landlord",
                page_number=1,
                source_span="Apex Properties LLC",
            ),
            ExtractedParty.create(
                document_id=doc1_id,
                name="Nexus Tech Inc",
                role="Tenant",
                page_number=1,
                source_span="Nexus Tech Inc",
            ),
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc1_id,
                raw_text="January 1, 2026",
                normalized_date="2026-01-01",
                date_type="effective_date",
                description="Commencement Date",
                page_number=1,
                source_span="January 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc1_id,
                obligor="Tenant",
                duty="provide 30 days notice prior to lease expiration",
                trigger="expiration",
                deadline="30 days",
                page_start=2,
                page_end=2,
                source_span="provide 30 days notice prior to lease expiration",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc1_id,
                title="Maintenance Responsibilities",
                category="general",
                clause_identifier="Section 4",
                text="Landlord shall provide maintenance.",
                page_start=2,
                page_end=2,
                source_span="Landlord shall provide maintenance.",
            )
        ],
        review_flags=[],
    )

    # Extractions for Doc 2
    extraction_repo.save_understanding(
        document_id=doc2_id,
        parties=[
            ExtractedParty.create(
                document_id=doc2_id,
                name="Apex Properties LLC",
                role="Landlord",
                page_number=1,
                source_span="Apex Properties LLC",
            ),
            ExtractedParty.create(
                document_id=doc2_id,
                name="Nexus Tech Inc",
                role="Tenant",
                page_number=1,
                source_span="Nexus Tech Inc",
            ),
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc2_id,
                raw_text="February 1, 2026",
                normalized_date="2026-02-01",
                date_type="effective_date",
                description="Commencement Date",
                page_number=1,
                source_span="February 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc2_id,
                obligor="Tenant",
                duty="provide 60 days written notice for renewal",
                trigger="renewal",
                deadline="60 days",
                page_start=2,
                page_end=2,
                source_span="provide 60 days written notice for renewal",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc2_id,
                title="Parking Space Allocation",
                category="general",
                clause_identifier="Addendum Clause 1",
                text="Parking space allocated in Section B.",
                page_start=2,
                page_end=2,
                source_span="Parking space allocated in Section B.",
            )
        ],
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
    }


def test_golden_lease_comparison_accuracy(golden_env: dict[str, Any]) -> None:
    """Evaluate end-to-end comparison accuracy on golden lease dataset."""
    service = golden_env["service"]
    user_id = golden_env["user_id"]
    doc1_id = golden_env["doc1_id"]
    doc2_id = golden_env["doc2_id"]

    comparison = service.generate_comparison(
        document_ids=[doc1_id, doc2_id],
        user_id=user_id,
        title="Commercial Lease vs 2026 Addendum",
    )

    # 1. Parties match
    parties_findings = [
        f for f in comparison.findings if f.category == ComparisonCategory.PARTIES
    ]
    assert len(parties_findings) >= 2
    for pf in parties_findings:
        assert pf.classification == DifferenceClassification.MATCH
        assert pf.trust_tier == TrustTier.DOCUMENT_FACT

    # 2. Date inconsistency detected (Jan 1, 2026 vs Feb 1, 2026)
    date_finding = next(
        f for f in comparison.findings if f.category == ComparisonCategory.DATES
    )
    assert (
        date_finding.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
    )
    assert "January 1, 2026" in date_finding.description
    assert "February 1, 2026" in date_finding.description
    assert len(date_finding.lawyer_questions) > 0

    # 3. Notice timeframe inconsistency (30 days vs 60 days)
    notice_finding = next(
        f
        for f in comparison.findings
        if f.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
        and f.category
        in (
            ComparisonCategory.NOTICE,
            ComparisonCategory.TERMINATION,
            ComparisonCategory.OBLIGATIONS,
        )
    )
    assert "30 Days vs 60 Days" in notice_finding.title or "30" in notice_finding.title

    # 4. Present in one only clauses
    present_findings = [
        f
        for f in comparison.findings
        if f.classification == DifferenceClassification.PRESENT_IN_ONE_ONLY
    ]
    assert len(present_findings) >= 1
    for pf in present_findings:
        assert "not identified in the extracted content" in pf.description

    # 5. Evidence validity invariant across all findings
    for f in comparison.findings:
        for ref in f.evidence_references:
            assert ref.validation_status == EvidenceValidationStatus.VALID
