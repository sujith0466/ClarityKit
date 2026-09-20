import pytest

from app.evidence.models import (
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.qa.models import (
    AnswerClaim,
    DocumentNotFoundError,
    DocumentNotReadyForQAError,
    InvalidQuestionError,
    QAMessage,
    QASession,
    QASessionNotFoundError,
    RetrievalSufficiency,
)
from app.qa.validation import (
    MAX_QUESTION_LENGTH,
    validate_question_text,
    validate_session_title,
)
from app.trust.models import SafetyStatus, TrustTier


class TestQAModels:
    """Unit tests for Q&A domain models, validation, and serialization."""

    def test_answer_claim_to_and_from_dict(self) -> None:
        ev = EvidenceReference(
            document_id="doc-123",
            page_start=2,
            page_end=2,
            source_span="Either party may terminate upon 30 days notice.",
            match_type=EvidenceMatchType.EXACT,
            validation_status=EvidenceValidationStatus.VALID,
        )
        claim = AnswerClaim(
            id="claim-1",
            claim_text="Termination notice requires 30 days.",
            claim_type="document_fact",
            evidence=ev,
            trust_tier=TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus.SAFE,
            is_valid=True,
            validation_reason="Exact match on page 2.",
        )

        data = claim.to_dict()
        assert data["id"] == "claim-1"
        assert data["trust_tier"] == "DOCUMENT_FACT"
        assert data["evidence"]["page_start"] == 2

        restored = AnswerClaim.from_dict(data)
        assert restored.id == claim.id
        assert restored.claim_text == claim.claim_text
        assert restored.trust_tier == TrustTier.DOCUMENT_FACT
        assert restored.evidence is not None
        assert restored.evidence.source_span == ev.source_span

    def test_qa_message_serialization(self) -> None:
        msg = QAMessage(
            id="msg-1",
            session_id="sess-1",
            document_id="doc-123",
            question_text="How can either party terminate?",
            answer_text="Either party may terminate by providing 30 days notice.",
            trust_tier=TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus.SAFE,
            evidence_coverage=1.0,
            is_grounded=True,
            claims=[
                AnswerClaim(
                    id="c-1",
                    claim_text="30 days notice required.",
                    claim_type="document_fact",
                    trust_tier=TrustTier.DOCUMENT_FACT,
                )
            ],
            evidence_references=[
                {
                    "claim_id": "c-1",
                    "page_start": 2,
                    "page_end": 2,
                    "source_span": "30 days notice",
                }
            ],
        )

        data = msg.to_dict()
        assert data["id"] == "msg-1"
        assert data["evidence_coverage"] == 1.0
        assert len(data["claims"]) == 1

        restored = QAMessage.from_dict(data)
        assert restored.id == "msg-1"
        assert restored.trust_tier == TrustTier.DOCUMENT_FACT
        assert restored.is_grounded is True
        assert len(restored.claims) == 1

    def test_qa_session_serialization(self) -> None:
        session = QASession(
            id="sess-1",
            document_id="doc-123",
            title="Custom Session Title",
            messages=[
                QAMessage(
                    id="m-1",
                    session_id="sess-1",
                    document_id="doc-123",
                    question_text="Who signed?",
                    answer_text="Acme Corp and Beta LLC.",
                    trust_tier=TrustTier.DOCUMENT_FACT,
                    safety_status=SafetyStatus.SAFE,
                    evidence_coverage=1.0,
                    is_grounded=True,
                )
            ],
        )

        data = session.to_dict()
        assert data["id"] == "sess-1"
        assert data["title"] == "Custom Session Title"
        assert len(data["messages"]) == 1

        restored = QASession.from_dict(data)
        assert restored.id == session.id
        assert len(restored.messages) == 1

    def test_question_validation_success(self) -> None:
        q = "   What is the governing law?   "
        clean = validate_question_text(q)
        assert clean == "What is the governing law?"

    def test_question_validation_empty_fails(self) -> None:
        with pytest.raises(InvalidQuestionError, match="cannot be empty"):
            validate_question_text("")

        with pytest.raises(InvalidQuestionError, match="cannot be empty"):
            validate_question_text("   \n\t  ")

        with pytest.raises(InvalidQuestionError, match="cannot be empty"):
            validate_question_text(None)

    def test_question_validation_length_exceeded_fails(self) -> None:
        long_q = "a" * (MAX_QUESTION_LENGTH + 1)
        with pytest.raises(InvalidQuestionError, match="exceeds maximum limit"):
            validate_question_text(long_q)

    def test_session_title_validation(self) -> None:
        assert validate_session_title(None) == "Document Q&A Session"
        assert validate_session_title("   ") == "Document Q&A Session"
        assert validate_session_title("My Agreement Thread") == "My Agreement Thread"

    def test_retrieval_sufficiency_enum(self) -> None:
        assert RetrievalSufficiency.SUFFICIENT.value == "sufficient"
        assert RetrievalSufficiency.WEAK.value == "weak"
        assert RetrievalSufficiency.NONE.value == "none"

    def test_domain_exceptions(self) -> None:
        assert issubclass(DocumentNotFoundError, Exception)
        assert issubclass(DocumentNotReadyForQAError, Exception)
        assert issubclass(QASessionNotFoundError, Exception)
