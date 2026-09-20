import uuid

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.repository import InMemoryEvidenceRepository
from app.evidence.service import EvidenceService
from app.extraction.models import (
    ClauseCategory,
    ExtractedClause,
    ExtractedParty,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.trust.models import (
    DocumentNotFoundError,
    DocumentNotReadyForTrustError,
    InvalidTrustInputError,
    SafetyStatus,
    TrustTier,
)
from app.trust.repository import InMemoryTrustRepository
from app.trust.service import TrustService


def _create_mock_service() -> tuple[TrustService, str, str]:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    evidence_repo = InMemoryEvidenceRepository(document_repository=doc_repo)
    trust_repo = InMemoryTrustRepository()

    user_id = "test-user-1"
    doc_id = str(uuid.uuid4())

    doc = Document(
        user_id=user_id,
        filename="lease_agreement.txt",
        storage_key="/tmp/lease.txt",
        file_size_bytes=1024,
        content_type="text/plain",
        content_hash="abcd" * 16,
        document_id=doc_id,
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    p1 = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        text="LANDLORD: John Doe\nTENANT: Jane Smith\nRent is $1200 per month.",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc_id, [p1])

    party = ExtractedParty.create(
        document_id=doc_id,
        name="John Doe",
        role="Landlord",
        source_span="LANDLORD: John Doe",
        page_number=1,
    )
    clause = ExtractedClause.create(
        document_id=doc_id,
        clause_identifier="1.1",
        title="Rent Amount",
        category=ClauseCategory.PAYMENT.value,
        text="Rent is $1200 per month.",
        page_start=1,
        page_end=1,
        source_span="Rent is $1200 per month.",
    )

    extraction_repo.save_understanding(
        document_id=doc_id,
        parties=[party],
        clauses=[clause],
        obligations=[],
        dates=[],
        review_flags=[],
    )

    evidence_service = EvidenceService(
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        evidence_repository=evidence_repo,
    )

    trust_service = TrustService(
        document_repository=doc_repo,
        evidence_service=evidence_service,
        trust_repository=trust_repo,
    )

    return trust_service, doc_id, user_id


def test_trust_service_generates_report() -> None:
    service, doc_id, user_id = _create_mock_service()
    report = service.get_document_trust_report(doc_id, user_id)
    assert report.document_id == doc_id
    assert report.total_claims >= 2
    assert report.evidence_coverage == 1.0
    assert report.overall_safety_status == SafetyStatus.SAFE
    assert report.tier_counts["DOCUMENT_FACT"] >= 2


def test_trust_service_unauthorized_document() -> None:
    service, doc_id, _ = _create_mock_service()
    with pytest.raises(DocumentNotFoundError):
        service.get_document_trust_report(doc_id, "different-user")


def test_trust_service_unready_document() -> None:
    service, doc_id, user_id = _create_mock_service()
    doc = service._doc_repo.get_by_id(doc_id)
    assert doc is not None
    doc.status = DocumentStatus.QUEUED
    service._doc_repo.save(doc)
    with pytest.raises(DocumentNotReadyForTrustError):
        service.get_document_trust_report(doc_id, user_id)


def test_trust_service_ad_hoc_claims_evaluation() -> None:
    service, doc_id, user_id = _create_mock_service()
    ad_hoc_input = [
        {
            "claim_text": "Tenant is Jane Smith.",
            "claim_type": "party",
            "evidence": {
                "page_start": 1,
                "page_end": 1,
                "source_span": "TENANT: Jane Smith",
            },
        },
        {
            "claim_text": "Is the late fee enforceable?",
            "claim_type": "general_fact",
            "evidence": {
                "page_start": 1,
                "page_end": 1,
                "source_span": "Rent is $1200 per month.",
            },
        },
    ]
    assessed = service.assess_ad_hoc_claims(doc_id, user_id, ad_hoc_input)
    assert len(assessed) == 2
    assert assessed[0].trust_assessment.trust_tier == TrustTier.DOCUMENT_FACT
    assert (
        assessed[1].trust_assessment.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    )


def test_trust_service_ad_hoc_payload_limit() -> None:
    service, doc_id, user_id = _create_mock_service()
    oversized = [{"claim_text": f"claim {i}"} for i in range(55)]
    with pytest.raises(InvalidTrustInputError):
        service.assess_ad_hoc_claims(doc_id, user_id, oversized)
