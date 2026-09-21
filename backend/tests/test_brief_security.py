"""Security and isolation tests for Lawyer Preparation Briefs."""

import pytest

from app.auth.models import User
from app.brief.models import (
    BriefNotFoundError,
    DocumentNotFoundError,
)
from app.brief.repository import InMemoryBriefRepository
from app.brief.service import BriefService
from app.brief.validation import contains_forbidden_legal_claims, sanitize_neutral_text
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    ExtractedParty,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.reasoning.gateway import ReasoningGateway


def test_tenant_isolation_unauthorized_user() -> None:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    brief_repo = InMemoryBriefRepository(document_repository=doc_repo)

    user_a = User(
        user_id="user-a", email="a@example.com", password_hash="dummy", name="User A"
    )
    user_b = User(
        user_id="user-b", email="b@example.com", password_hash="dummy", name="User B"
    )

    doc = Document(
        document_id="doc-isolated-1",
        user_id=user_a.user_id,
        filename="Secret_Contract.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        storage_key="test_storage",
        content_hash="sha-sec",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text="Secret confidential text",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page])

    parties = [
        ExtractedParty.create(
            document_id=doc.id,
            name="Alpha Corp",
            role="Client",
            page_number=1,
            source_span="Alpha Corp",
        )
    ]
    extraction_repo.save_understanding(
        document_id=doc.id,
        parties=parties,
        clauses=[],
        obligations=[],
        dates=[],
        review_flags=[],
    )

    service = BriefService(
        brief_repository=brief_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        reasoning_gateway=ReasoningGateway(),
    )

    brief_a = service.generate_brief(doc.id, user_a.user_id)
    assert brief_a is not None

    # User B cannot get brief by document
    with pytest.raises(DocumentNotFoundError):
        service.get_brief_by_document(doc.id, user_b.user_id)

    # User B cannot get brief by id
    with pytest.raises(BriefNotFoundError):
        service.get_brief_by_id(brief_a.id, user_b.user_id)

    # User B cannot delete brief
    with pytest.raises(BriefNotFoundError):
        service.delete_brief(brief_a.id, user_b.user_id)

    # User B cannot export PDF
    with pytest.raises(BriefNotFoundError):
        service.export_brief_pdf(brief_a.id, user_b.user_id)


def test_forbidden_legal_advice_sanitization() -> None:
    harmful_text = (
        "You should sign this agreement immediately because you will win in court. "
        "This is illegal."
    )
    assert contains_forbidden_legal_claims(harmful_text) is True

    sanitized = sanitize_neutral_text(harmful_text)
    assert "you should sign" not in sanitized.lower()
    assert "you will win" not in sanitized.lower()


def test_pdf_export_contains_no_secrets() -> None:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    brief_repo = InMemoryBriefRepository(document_repository=doc_repo)

    user = User(
        user_id="user-sec",
        email="sec@example.com",
        password_hash="dummy",
        name="Sec User",
    )

    doc = Document(
        document_id="doc-sec",
        user_id=user.user_id,
        filename="Doc.pdf",
        content_type="application/pdf",
        file_size_bytes=512,
        storage_key="test_storage",
        content_hash="sha-sec",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text="Standard contract text.",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page])

    extraction_repo.save_understanding(
        document_id=doc.id,
        parties=[],
        clauses=[],
        obligations=[],
        dates=[],
        review_flags=[],
    )

    service = BriefService(
        brief_repository=brief_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        reasoning_gateway=ReasoningGateway(),
    )

    brief = service.generate_brief(doc.id, user.user_id)
    pdf_bytes = service.export_brief_pdf(brief.id, user.user_id)
    pdf_str = pdf_bytes.decode("latin1", errors="ignore")

    # Assert no secret keys or internal system prompt leaking in PDF
    assert "password" not in pdf_str.lower()
    assert "jwt_secret" not in pdf_str.lower()
    assert "db_password" not in pdf_str.lower()
    assert "<document_evidence>" not in pdf_str
