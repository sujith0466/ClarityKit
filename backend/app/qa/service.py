import logging
import uuid
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import (
    DocumentRepository,
    in_memory_document_repository,
)
from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.evidence.service import EvidenceService
from app.evidence.validators import EvidenceValidator
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)
from app.qa.models import (
    AnswerClaim,
    DocumentNotFoundError,
    DocumentNotReadyForQAError,
    QAMessage,
    QASession,
    QASessionNotFoundError,
    RetrievalSufficiency,
)
from app.qa.repository import QARepository, get_qa_repository
from app.qa.validation import validate_question_text, validate_session_title
from app.reasoning.gateway import ReasoningGateway, get_reasoning_gateway
from app.reasoning.models import QAReasoningRequest
from app.retrieval.retrieval_service import RetrievalService
from app.trust.classifier import TrustClassifier
from app.trust.models import (
    SafetyStatus,
    TrustTier,
)
from app.trust.service import TrustService

logger = logging.getLogger(__name__)


class QAService:
    """Coordinates document-scoped, evidence-grounded Question Answering."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        retrieval_service: RetrievalService | None = None,
        page_repository: PageRepository | None = None,
        evidence_service: EvidenceService | None = None,
        trust_service: TrustService | None = None,
        qa_repository: QARepository | None = None,
        reasoning_gateway: ReasoningGateway | None = None,
        trust_classifier: TrustClassifier | None = None,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._retrieval_service = retrieval_service or RetrievalService(
            document_repository=self._doc_repo
        )
        self._page_repo = page_repository or in_memory_page_repository
        self._evidence_service = evidence_service or EvidenceService(
            document_repository=self._doc_repo,
            page_repository=self._page_repo,
        )
        self._trust_service = trust_service or TrustService(
            document_repository=self._doc_repo,
            evidence_service=self._evidence_service,
        )
        self._qa_repo = qa_repository or get_qa_repository()
        self._reasoning_gateway = reasoning_gateway or get_reasoning_gateway()
        self._trust_classifier = trust_classifier or TrustClassifier()

    def create_session(
        self, document_id: str, user_id: str, title: str | None = None
    ) -> QASession:
        """Create a new Q&A session for an owned document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        clean_title = validate_session_title(title)
        session = QASession(
            id=str(uuid.uuid4()),
            document_id=document_id,
            title=clean_title,
        )
        return self._qa_repo.create_session(session, user_id)

    def get_session(self, session_id: str, user_id: str) -> QASession:
        """Retrieve an owned Q&A session with its message history."""
        session = self._qa_repo.get_session(session_id, user_id)
        if not session:
            raise QASessionNotFoundError("Q&A session not found or access denied.")
        return session

    def list_sessions(self, document_id: str, user_id: str) -> list[QASession]:
        """List all Q&A sessions for an owned document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        return self._qa_repo.list_sessions_by_document(document_id, user_id)

    def list_document_messages(self, document_id: str, user_id: str) -> list[QAMessage]:
        """List all Q&A messages for an owned document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        return self._qa_repo.get_messages_by_document(document_id, user_id)

    def get_message(self, message_id: str, user_id: str) -> QAMessage:
        """Retrieve a single Q&A message by ID."""
        msg = self._qa_repo.get_message_by_id(message_id, user_id)
        if not msg:
            raise QASessionNotFoundError("Q&A message not found or access denied.")
        return msg

    def evaluate_retrieval_sufficiency(
        self, retrieval_results: list[Any]
    ) -> RetrievalSufficiency:
        """Deterministically assess whether retrieved context is sufficient."""
        if not retrieval_results:
            return RetrievalSufficiency.NONE

        # Check top result score
        top_score = getattr(retrieval_results[0], "score", 1.0)
        if top_score < 0.1:
            return RetrievalSufficiency.WEAK

        return RetrievalSufficiency.SUFFICIENT

    def ask_question(
        self,
        document_id: str,
        user_id: str,
        question: str,
        session_id: str | None = None,
    ) -> QAMessage:
        """Execute the complete grounded Q&A pipeline.

        1. Document ownership and readiness verification.
        2. Input validation and prompt injection containment.
        3. Document-scoped vector retrieval.
        4. Retrieval sufficiency evaluation.
        5. Generative answer reasoning via ReasoningGateway.
        6. Mechanical citation validation via Phase 7 EvidenceValidator.
        7. Hard No-Evidence Rule enforcement.
        8. Deterministic Trust & Safety classification via Phase 8 TrustClassifier.
        9. Answer assembly and sensitive-aware persistence.
        """
        clean_question = validate_question_text(question)

        # 1. Verify document ownership and readiness
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForQAError(
                f"Document is in status '{doc.status.value}', "
                "must be processed and ready before asking questions."
            )

        # Ensure session exists or create one
        active_session_id = session_id
        if active_session_id:
            session = self._qa_repo.get_session(active_session_id, user_id)
            if not session or session.document_id != document_id:
                raise QASessionNotFoundError(
                    "Specified Q&A session not found for this document."
                )
        else:
            existing_sessions = self._qa_repo.list_sessions_by_document(
                document_id, user_id
            )
            if existing_sessions:
                active_session_id = existing_sessions[0].id
            else:
                new_session = self.create_session(
                    document_id=document_id,
                    user_id=user_id,
                    title="Document Q&A Session",
                )
                active_session_id = new_session.id

        # 2. Document-scoped retrieval
        try:
            retrieval_results = self._retrieval_service.retrieve(
                user_id=user_id,
                query=clean_question,
                document_id=document_id,
                top_k=5,
            )
        except Exception as e:
            logger.warning("Vector retrieval failed for doc %s: %s", document_id, e)
            retrieval_results = []

        context_chunks: list[dict[str, Any]] = []
        for r in retrieval_results:
            context_chunks.append(
                {
                    "chunk_id": r.chunk_id,
                    "chunk_text": r.text,
                    "page_number": r.page_start,
                    "page_start": r.page_start,
                    "page_end": r.page_end,
                    "score": r.similarity,
                }
            )

        sufficiency = self.evaluate_retrieval_sufficiency(retrieval_results)

        # 3. If zero chunks from retrieval, fetch fallback page text
        if not context_chunks:
            pages = self._page_repo.get_pages_by_document(document_id)
            for p in pages[:3]:
                context_chunks.append(
                    {
                        "chunk_id": p.id,
                        "chunk_text": p.text,
                        "page_number": p.page_number,
                        "page_start": p.page_number,
                        "page_end": p.page_number,
                        "score": 1.0,
                    }
                )

        # 4. Generate answer via ReasoningGateway
        reasoning_req = QAReasoningRequest(
            document_id=document_id,
            question=clean_question,
            context_chunks=context_chunks,
            metadata={"filename": doc.filename, "sufficiency": sufficiency.value},
        )
        raw_qa = self._reasoning_gateway.generate_grounded_answer(reasoning_req)

        # 5. Fetch authoritative page texts for Phase 7 mechanical validation
        pages = self._page_repo.get_pages_by_document(document_id)
        page_texts: dict[int, str] = {p.page_number: p.text for p in pages}

        # 6. Mechanical evidence validation via Phase 7 EvidenceValidator
        raw_claims = raw_qa.claims
        phase7_claims: list[Claim] = []

        for rc in raw_claims:
            ev_ref: EvidenceReference | None = None
            if rc.source_span:
                p_start = rc.page_start or 1
                p_end = rc.page_end or p_start
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=p_start,
                    page_end=p_end,
                    source_span=rc.source_span,
                    section=rc.section,
                    clause_id=rc.clause_id,
                )

            claim_type_str = (rc.claim_type or "general_fact").lower()
            claim_type = (
                ClaimType(claim_type_str)
                if claim_type_str in [c.value for c in ClaimType]
                else ClaimType.GENERAL_FACT
            )

            claim_entity = Claim.create(
                document_id=document_id,
                claim_text=rc.claim_text,
                claim_type=claim_type,
                evidence=ev_ref,
            )
            phase7_claims.append(claim_entity)

        validated_claims, _coverage = EvidenceValidator.validate_claims(
            phase7_claims, page_texts
        )

        # 7. Apply Hard "No-Evidence" Rule & Phase 8 Trust Classification
        final_claims: list[AnswerClaim] = []
        valid_evidence_count = 0
        total_document_facts = 0

        for vc in validated_claims:
            is_valid_evidence = (
                vc.evidence is not None
                and vc.validation_status == EvidenceValidationStatus.VALID
            )

            # Evaluate through deterministic TrustClassifier
            assessment = self._trust_classifier.classify_claim(vc)

            # Hard Invariant: If claim lacks valid evidence, it cannot be DOCUMENT_FACT
            tier = assessment.trust_tier
            safety = assessment.safety_status

            if tier == TrustTier.DOCUMENT_FACT and not is_valid_evidence:
                tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                safety = SafetyStatus.UNSUPPORTED

            if tier == TrustTier.DOCUMENT_FACT:
                total_document_facts += 1
                if is_valid_evidence:
                    valid_evidence_count += 1

            reason_str = (
                vc.evidence.validation_reason
                if vc.evidence and vc.evidence.validation_reason
                else vc.validation_status.value
            )

            ac = AnswerClaim(
                id=vc.id,
                claim_text=vc.claim_text,
                claim_type=vc.claim_type.value,
                evidence=vc.evidence,
                trust_tier=tier,
                safety_status=safety,
                is_valid=is_valid_evidence,
                validation_reason=reason_str,
            )
            final_claims.append(ac)

        # 8. Overall Trust Tier and Safety Status
        if raw_qa.requires_professional_review:
            overall_trust = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            overall_safety = SafetyStatus.REVIEW_REQUIRED
        elif any(
            item.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
            for item in final_claims
        ):
            overall_trust = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            overall_safety = SafetyStatus.REVIEW_REQUIRED
        elif any(item.trust_tier == TrustTier.INTERPRETATION for item in final_claims):
            overall_trust = TrustTier.INTERPRETATION
            overall_safety = SafetyStatus.LIMITED
        elif any(
            item.trust_tier == TrustTier.GENERAL_INFORMATION for item in final_claims
        ):
            overall_trust = TrustTier.GENERAL_INFORMATION
            overall_safety = SafetyStatus.SAFE
        elif final_claims:
            overall_trust = TrustTier.DOCUMENT_FACT
            overall_safety = SafetyStatus.SAFE
        else:
            overall_trust = TrustTier.GENERAL_INFORMATION
            overall_safety = SafetyStatus.SAFE

        coverage_ratio = (
            (valid_evidence_count / total_document_facts)
            if total_document_facts > 0
            else (1.0 if not final_claims else 0.0)
        )
        is_grounded = bool(valid_evidence_count > 0 and coverage_ratio >= 0.5)

        # Extract evidence reference summaries
        evidence_references: list[dict[str, Any]] = []
        for ac_ref in final_claims:
            if ac_ref.evidence and ac_ref.is_valid:
                evidence_references.append(
                    {
                        "claim_id": ac_ref.id,
                        "claim_text": ac_ref.claim_text,
                        "page_start": ac_ref.evidence.page_start,
                        "page_end": ac_ref.evidence.page_end,
                        "source_span": ac_ref.evidence.source_span,
                    }
                )

        # 9. Assemble and persist QAMessage
        message = QAMessage(
            id=str(uuid.uuid4()),
            session_id=active_session_id,
            document_id=document_id,
            question_text=clean_question,
            answer_text=raw_qa.answer_text,
            trust_tier=overall_trust,
            safety_status=overall_safety,
            evidence_coverage=round(coverage_ratio, 4),
            is_grounded=is_grounded,
            claims=final_claims,
            evidence_references=evidence_references,
        )

        saved_message = self._qa_repo.save_message(message, user_id)
        return saved_message
