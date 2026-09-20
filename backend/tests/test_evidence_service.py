import uuid

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.models import (
    EvidenceValidationStatus,
)
from app.evidence.repository import InMemoryEvidenceRepository
from app.evidence.service import EvidenceService
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


def test_evidence_service_end_to_end_synthetic_lease() -> None:
    user_id = "user-test-1"
    doc_id = str(uuid.uuid4())

    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extract_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    evidence_repo = InMemoryEvidenceRepository(document_repository=doc_repo)

    doc = Document(
        user_id=user_id,
        filename="commercial_lease.pdf",
        content_type="application/pdf",
        file_size_bytes=1000,
        storage_key="key1",
        content_hash="hash1",
        document_id=doc_id,
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    p1 = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        text=(
            "LEASE AGREEMENT\nThis Lease Agreement is entered into between "
            'Landlord Properties LLC ("Landlord") and Tech Innovations Inc ("Tenant").'
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    p2 = DocumentPage.create(
        document_id=doc_id,
        page_number=2,
        text=(
            "SECTION 3: RENT\nTenant shall pay Base Rent of $4,000 per month on "
            "or before the 1st day of each calendar month.\n\nSECTION 4: TERM\n"
            "The lease commences on September 1, 2026 and expires on August 31, 2028."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc_id, [p1, p2])

    party1 = ExtractedParty.create(
        document_id=doc_id,
        name="Landlord Properties LLC",
        role="Landlord",
        page_number=1,
        source_span='Landlord Properties LLC ("Landlord")',
    )
    party2 = ExtractedParty.create(
        document_id=doc_id,
        name="Tech Innovations Inc",
        role="Tenant",
        page_number=1,
        source_span='Tech Innovations Inc ("Tenant")',
    )
    clause1 = ExtractedClause.create(
        document_id=doc_id,
        clause_identifier="3",
        title="RENT",
        category="payment",
        text=(
            "Tenant shall pay Base Rent of $4,000 per month on or before the 1st "
            "day of each calendar month."
        ),
        page_start=2,
        page_end=2,
        source_span="SECTION 3: RENT",
    )
    obl1 = ExtractedObligation.create(
        document_id=doc_id,
        obligor="Tenant",
        duty="pay Base Rent of $4,000 per month",
        trigger=None,
        deadline="1st day of each calendar month",
        page_start=2,
        page_end=2,
        source_span=(
            "Tenant shall pay Base Rent of $4,000 per month on or before the "
            "1st day of each calendar month."
        ),
    )
    date1 = ExtractedDate.create(
        document_id=doc_id,
        date_type="effective_date",
        raw_text="September 1, 2026",
        normalized_date="2026-09-01",
        description="Lease Commencement Date",
        page_number=2,
        source_span="commences on September 1, 2026",
    )
    flag1 = ExtractedReviewFlag.create(
        document_id=doc_id,
        flag_type="general_notice",
        title="Rent Due Date",
        description="Rent is payable on the 1st of each month.",
        severity="low",
        page_start=2,
        page_end=2,
        source_span=(
            "Tenant shall pay Base Rent of $4,000 per month on or before the "
            "1st day of each calendar month."
        ),
    )

    extract_repo.save_understanding(
        document_id=doc_id,
        parties=[party1, party2],
        clauses=[clause1],
        obligations=[obl1],
        dates=[date1],
        review_flags=[flag1],
    )

    service = EvidenceService(
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extract_repo,
        evidence_repository=evidence_repo,
    )

    report = service.generate_document_evidence(document_id=doc_id, user_id=user_id)

    assert report.document_id == doc_id
    assert report.coverage.total_claims == 6
    assert report.coverage.valid_claims == 6
    assert report.coverage.invalid_claims == 0
    assert report.coverage.coverage_ratio == 1.0
    assert report.coverage.is_fully_covered is True

    retrieved = service.get_document_evidence(document_id=doc_id, user_id=user_id)
    assert retrieved.coverage.valid_claims == 6


def test_evidence_service_ad_hoc_claim_validation_bounded() -> None:
    user_id = "user-test-2"
    doc_id = str(uuid.uuid4())

    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    evidence_repo = InMemoryEvidenceRepository(document_repository=doc_repo)

    doc = Document(
        user_id=user_id,
        filename="service_agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=500,
        storage_key="key2",
        content_hash="hash2",
        document_id=doc_id,
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    p1 = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        text=(
            "The Provider shall deliver the final audit report within "
            "forty-five (45) days."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc_id, [p1])

    service = EvidenceService(
        document_repository=doc_repo,
        page_repository=page_repo,
        evidence_repository=evidence_repo,
    )

    raw_claims = [
        {
            "claim_text": "Provider must deliver report within 45 days",
            "claim_type": "obligation",
            "evidence": {
                "page_start": 1,
                "page_end": 1,
                "source_span": (
                    "Provider shall deliver the final audit report within "
                    "forty-five (45) days"
                ),
            },
        },
        {
            "claim_text": "Provider must deliver report within 90 days",
            "claim_type": "obligation",
            "evidence": {
                "page_start": 1,
                "page_end": 1,
                "source_span": (
                    "Provider shall deliver the final audit report within "
                    "ninety (90) days"
                ),
            },
        },
        {
            "claim_text": "Provider report delivery deadline",
            "claim_type": "date",
            "evidence": {
                "page_start": 4,
                "page_end": 4,
                "source_span": "within forty-five (45) days",
            },
        },
    ]

    report = service.validate_ad_hoc_claims(
        document_id=doc_id,
        user_id=user_id,
        raw_claims=raw_claims,
    )

    assert report.coverage.total_claims == 3
    assert report.coverage.valid_claims == 1
    assert report.coverage.invalid_claims == 2
    assert report.coverage.coverage_ratio == 0.3333
    assert report.claims[0].validation_status == EvidenceValidationStatus.VALID
    assert report.claims[1].validation_status == EvidenceValidationStatus.INVALID
    assert report.claims[2].validation_status == EvidenceValidationStatus.INVALID
