import uuid

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    DocumentNotFoundError,
    DocumentNotReadyForExtractionError,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.extraction.service import ExtractionService
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.reasoning.gateway import ReasoningGateway


@pytest.fixture
def service_setup() -> tuple[
    ExtractionService,
    InMemoryDocumentRepository,
    InMemoryPageRepository,
    InMemoryExtractionRepository,
]:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    ext_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    gateway = ReasoningGateway()
    service = ExtractionService(
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=ext_repo,
        reasoning_gateway=gateway,
    )
    return service, doc_repo, page_repo, ext_repo


def test_extract_lease_agreement(
    service_setup: tuple[
        ExtractionService,
        InMemoryDocumentRepository,
        InMemoryPageRepository,
        InMemoryExtractionRepository,
    ],
) -> None:
    service, doc_repo, page_repo, _ = service_setup
    user_id = "user-lease"
    doc_id = str(uuid.uuid4())

    # Create READY document
    doc = Document(
        document_id=doc_id,
        user_id=user_id,
        filename="Lease_Agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=4096,
        storage_key="/tmp/lease.pdf",
        content_hash="hash-lease",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    # Add processed pages
    page1_text = (
        "RESIDENTIAL LEASE AGREEMENT\n"
        "This Agreement is entered into by and between Oakwood Properties LLC"
        ' ("Landlord") and Alice Walker ("Tenant").\n'
        "Effective Date: January 15, 2026.\n\n"
        "1. Rent Payment. Tenant shall pay monthly rent of $2,400 on or before the 1st "
        "day of each month.\n"
        "2. Security Deposit. Tenant shall deposit $2,400 upon execution of this "
        "agreement."
    )
    page2_text = (
        "3. Term and Renewal. This Lease will automatically renew for successive "
        "1-year terms unless Tenant provides written notice 90 days prior to "
        "expiration.\n"
        "4. Maintenance. Landlord shall maintain structural components in good repair."
    )

    page_repo.save_pages(
        doc_id,
        [
            DocumentPage.create(doc_id, 1, page1_text, ExtractionMethod.NATIVE),
            DocumentPage.create(doc_id, 2, page2_text, ExtractionMethod.NATIVE),
        ],
    )

    # Execute extraction
    understanding = service.extract_document(doc_id, user_id)

    assert understanding.document_id == doc_id
    assert len(understanding.parties) >= 2
    party_names = [p.name for p in understanding.parties]
    assert "Oakwood Properties LLC" in party_names
    assert "Alice Walker" in party_names

    assert len(understanding.clauses) >= 3
    clause_titles = [c.title for c in understanding.clauses]
    assert any("Rent" in t for t in clause_titles)
    assert any("Term" in t or "Renewal" in t for t in clause_titles)

    assert len(understanding.obligations) >= 2
    assert any("Tenant" in o.obligor for o in understanding.obligations)
    assert any("2,400" in o.duty for o in understanding.obligations)

    assert len(understanding.dates) >= 1
    assert any(d.normalized_date == "2026-01-15" for d in understanding.dates)

    assert len(understanding.review_flags) >= 1
    assert any(f.flag_type == "renewal_lock_in" for f in understanding.review_flags)


def test_extract_employment_agreement(
    service_setup: tuple[
        ExtractionService,
        InMemoryDocumentRepository,
        InMemoryPageRepository,
        InMemoryExtractionRepository,
    ],
) -> None:
    service, doc_repo, page_repo, _ = service_setup
    user_id = "user-emp"
    doc_id = str(uuid.uuid4())

    doc = Document(
        document_id=doc_id,
        user_id=user_id,
        filename="Employment_Contract.pdf",
        content_type="application/pdf",
        file_size_bytes=5120,
        storage_key="/tmp/emp.pdf",
        content_hash="hash-emp",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page1_text = (
        "EMPLOYMENT AGREEMENT\n"
        'between Apex Global Inc ("Employer") and Jordan Smith ("Employee").\n'
        "Commencement Date: 2026-06-01.\n\n"
        "1. Compensation. Employer shall pay Employee a base salary of $120,000 "
        "annually.\n"
        "2. Restrictive Covenants. Employee agrees to non-compete restrictions for "
        "12 months post-employment."
    )
    page_repo.save_pages(
        doc_id,
        [DocumentPage.create(doc_id, 1, page1_text, ExtractionMethod.NATIVE)],
    )

    understanding = service.extract_document(doc_id, user_id)
    assert len(understanding.parties) >= 2
    assert any(p.role == "Employer" for p in understanding.parties)
    assert any(p.role == "Employee" for p in understanding.parties)

    assert len(understanding.review_flags) >= 1
    assert any(
        f.flag_type == "restrictive_covenant" for f in understanding.review_flags
    )


def test_extraction_idempotency(
    service_setup: tuple[
        ExtractionService,
        InMemoryDocumentRepository,
        InMemoryPageRepository,
        InMemoryExtractionRepository,
    ],
) -> None:
    service, doc_repo, page_repo, ext_repo = service_setup
    user_id = "user-idemp"
    doc_id = str(uuid.uuid4())

    doc = Document(
        document_id=doc_id,
        user_id=user_id,
        filename="Contract.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="/tmp/c.pdf",
        content_hash="hash-c",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page_repo.save_pages(
        doc_id,
        [
            DocumentPage.create(
                doc_id,
                1,
                (
                    'Agreement between Vendor Co ("Seller") and Buyer Inc ("Buyer").\n'
                    "1. Payment. Buyer shall pay within 30 days."
                ),
                ExtractionMethod.NATIVE,
            )
        ],
    )

    # Run extraction first time
    res1 = service.extract_document(doc_id, user_id)
    party_count1 = len(res1.parties)
    clause_count1 = len(res1.clauses)

    # Run extraction second time
    res2 = service.extract_document(doc_id, user_id)
    assert len(res2.parties) == party_count1
    assert len(res2.clauses) == clause_count1


def test_extract_not_ready_document_raises(
    service_setup: tuple[
        ExtractionService,
        InMemoryDocumentRepository,
        InMemoryPageRepository,
        InMemoryExtractionRepository,
    ],
) -> None:
    service, doc_repo, _, _ = service_setup
    user_id = "user-pending"
    doc_id = str(uuid.uuid4())

    doc = Document(
        document_id=doc_id,
        user_id=user_id,
        filename="Doc.pdf",
        content_type="application/pdf",
        file_size_bytes=1000,
        storage_key="/tmp/doc.pdf",
        content_hash="hash-p",
        status=DocumentStatus.QUEUED,
    )
    doc_repo.save(doc)

    with pytest.raises(DocumentNotReadyForExtractionError):
        service.extract_document(doc_id, user_id)


def test_extract_nonexistent_document_raises(
    service_setup: tuple[
        ExtractionService,
        InMemoryDocumentRepository,
        InMemoryPageRepository,
        InMemoryExtractionRepository,
    ],
) -> None:
    service, _, _, _ = service_setup
    with pytest.raises(DocumentNotFoundError):
        service.extract_document("nonexistent-doc-id", "user-1")
