from typing import Any

import pytest

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.evidence.service import EvidenceService
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
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
def golden_env() -> dict[str, Any]:
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

    doc = Document(
        user_id="user-golden",
        filename="Commercial_Lease_Agreement.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="test-key",
        content_hash="sha-golden-lease",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    # Multi-page lease agreement
    page1 = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text=(
            "COMMERCIAL LEASE AGREEMENT entered into between Apex Properties "
            "('Landlord') and Nova Retail LLC ('Tenant'). The monthly rent "
            "shall be $4,500 due on the first day of each month."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2 = DocumentPage.create(
        document_id=doc.id,
        page_number=2,
        text=(
            "Tenant shall maintain general liability insurance in the amount "
            "of $1,000,000. Either party may terminate this lease upon 60 days "
            "written notice in the event of default."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page3 = DocumentPage.create(
        document_id=doc.id,
        page_number=3,
        text=(
            "This lease is governed by the laws of the State of California. "
            "Tenant shall keep all business records and trade secrets "
            "strictly confidential."
        ),
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page1, page2, page3])

    return {"service": qa_service, "doc": doc, "user_id": "user-golden"}


class TestQAGroundingGolden:
    """Golden fixtures validating mechanical citation correctness."""

    def test_case_1_explicit_rent_fact(self, golden_env: dict[str, Any]) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="What is the monthly rent amount?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "$4,500" in msg.answer_text
        assert msg.is_grounded is True
        assert any(
            "Page 1" in str(ev.get("page_start", "")) or ev.get("page_start") == 1
            for ev in msg.evidence_references
        )

    def test_case_2_parties_identification(self, golden_env: dict[str, Any]) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="Who are the contracting parties?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "Apex Properties" in msg.answer_text
        assert "Nova Retail" in msg.answer_text

    def test_case_3_termination_and_notice(self, golden_env: dict[str, Any]) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="How can either party terminate the lease?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "60 days" in msg.answer_text
        assert msg.is_grounded is True

    def test_case_4_governing_law(self, golden_env: dict[str, Any]) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="What is the governing law?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "California" in msg.answer_text

    def test_case_5_confidentiality(self, golden_env: dict[str, Any]) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="What are the confidentiality requirements?",
        )

        assert msg.trust_tier == TrustTier.DOCUMENT_FACT
        assert "confidential" in msg.answer_text.lower()

    def test_case_6_absent_fact_returns_fallback(
        self, golden_env: dict[str, Any]
    ) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question="Is there a pet deposit required?",
        )

        assert "does not contain enough information" in msg.answer_text

    def test_case_7_enforceability_triggers_professional_review(
        self, golden_env: dict[str, Any]
    ) -> None:
        service: QAService = golden_env["service"]
        doc: Document = golden_env["doc"]
        user_id: str = golden_env["user_id"]

        msg = service.ask_question(
            document_id=doc.id,
            user_id=user_id,
            question=(
                "Is the 60-day default termination clause legally "
                "valid and enforceable?"
            ),
        )

        assert msg.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
        assert msg.safety_status == SafetyStatus.REVIEW_REQUIRED
        assert "qualified legal professional" in msg.answer_text
