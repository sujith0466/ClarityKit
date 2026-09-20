from typing import Any

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.service import EvidenceService
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.qa.models import (
    DocumentNotFoundError,
    DocumentNotReadyForQAError,
)
from app.qa.repository import InMemoryQARepository
from app.qa.service import QAService
from app.reasoning.deterministic_provider import (
    DeterministicStructuredExtractionProvider,
)
from app.reasoning.gateway import ReasoningGateway
from app.retrieval.embeddings import (
    CachedEmbeddingProvider,
    DeterministicEmbeddingProvider,
)
from app.retrieval.repository import InMemoryVectorChunkRepository
from app.retrieval.retrieval_service import RetrievalService
from app.trust.models import SafetyStatus, TrustTier
from app.trust.service import TrustService


@pytest.fixture
def qa_fixture() -> dict[str, Any]:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    chunk_repo = InMemoryVectorChunkRepository(document_repository=doc_repo)
    embedding_provider = CachedEmbeddingProvider(DeterministicEmbeddingProvider())
    retrieval_service = RetrievalService(
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
        embedding_provider=embedding_provider,
    )
    evidence_service = EvidenceService(
        document_repository=doc_repo,
        page_repository=page_repo,
    )
    trust_service = TrustService(
        document_repository=doc_repo,
        evidence_service=evidence_service,
    )
    qa_repo = InMemoryQARepository()
    reasoning_gateway = ReasoningGateway(
        provider=DeterministicStructuredExtractionProvider()
    )

    qa_service = QAService(
        document_repository=doc_repo,
        retrieval_service=retrieval_service,
        page_repository=page_repo,
        evidence_service=evidence_service,
        trust_service=trust_service,
        qa_repository=qa_repo,
        reasoning_gateway=reasoning_gateway,
    )

    # Populate a ready test document
    doc = Document(
        user_id="user-1",
        filename="Test_Agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        storage_key="test-key",
        content_hash="abcd1234",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    # Populate pages
    page1_text = (
        "This Master Services Agreement is entered into by Acme Corp and Beta LLC. "
        "Either party may terminate this Agreement by giving 30 days written notice. "
        "This Agreement shall be governed by the laws of the State of Delaware."
    )
    page1 = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text=page1_text,
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page1])

    return {
        "doc": doc,
        "qa_service": qa_service,
        "doc_repo": doc_repo,
        "page_repo": page_repo,
        "qa_repo": qa_repo,
    }


class TestQAService:
    """Unit tests for QAService coordination and safety invariants."""

    def test_ask_grounded_question_success(self, qa_fixture: dict[str, Any]) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc: Document = qa_fixture["doc"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id="user-1",
            question="How can either party terminate the agreement?",
        )

        assert msg.document_id == doc.id
        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert msg.safety_status == SafetyStatus.SAFE
        assert msg.is_grounded is True
        assert msg.evidence_coverage > 0.0
        assert len(msg.evidence_references) > 0
        assert "30 days" in msg.answer_text

    def test_ask_governing_law_question(self, qa_fixture: dict[str, Any]) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc: Document = qa_fixture["doc"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id="user-1",
            question="What is the governing law?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "Delaware" in msg.answer_text
        assert msg.is_grounded is True

    def test_missing_facts_returns_safe_fallback(
        self, qa_fixture: dict[str, Any]
    ) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc: Document = qa_fixture["doc"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id="user-1",
            question="What is the price of the titanium widgets?",
        )

        assert "does not contain enough information" in msg.answer_text
        assert msg.trust_tier in (
            TrustTier.GENERAL_INFORMATION,
            TrustTier.DOCUMENT_FACT,
        )

    def test_legal_advice_question_flags_professional_review(
        self, qa_fixture: dict[str, Any]
    ) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc: Document = qa_fixture["doc"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id="user-1",
            question=(
                "Is this termination clause legally valid and enforceable in court?"
            ),
        )

        assert msg.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
        assert msg.safety_status == SafetyStatus.REVIEW_REQUIRED
        assert "qualified legal professional" in msg.answer_text

    def test_unready_document_raises_error(self, qa_fixture: dict[str, Any]) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc_repo: InMemoryDocumentRepository = qa_fixture["doc_repo"]

        unready_doc = Document(
            user_id="user-1",
            filename="Unready.pdf",
            content_type="application/pdf",
            file_size_bytes=512,
            storage_key="test-key-unready",
            content_hash="hash-unready",
            status=DocumentStatus.PROCESSING,
        )
        doc_repo.save(unready_doc)

        with pytest.raises(
            DocumentNotReadyForQAError, match="must be processed and ready"
        ):
            service.ask_question(
                document_id=unready_doc.id,
                user_id="user-1",
                question="Who are the parties?",
            )

    def test_non_existent_document_raises_404(self, qa_fixture: dict[str, Any]) -> None:
        service: QAService = qa_fixture["qa_service"]
        with pytest.raises(DocumentNotFoundError):
            service.ask_question(
                document_id="doc-nonexistent",
                user_id="user-1",
                question="Who signed?",
            )

    def test_session_lifecycle(self, qa_fixture: dict[str, Any]) -> None:
        service: QAService = qa_fixture["qa_service"]
        doc: Document = qa_fixture["doc"]

        session = service.create_session(
            document_id=doc.id,
            user_id="user-1",
            title="Custom Discussion",
        )
        assert session.title == "Custom Discussion"

        msg = service.ask_question(
            document_id=doc.id,
            user_id="user-1",
            question="Who are the parties?",
            session_id=session.id,
        )
        assert msg.session_id == session.id

        loaded_session = service.get_session(session.id, user_id="user-1")
        assert len(loaded_session.messages) == 1
        assert loaded_session.messages[0].id == msg.id

        sessions = service.list_sessions(doc.id, user_id="user-1")
        assert len(sessions) >= 1
