"""Service layer for assembling and managing Lawyer Preparation Briefs."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.brief.models import (
    BriefItem,
    BriefNotFoundError,
    BriefQuestion,
    BriefSection,
    BriefSourceType,
    DocumentNotFoundError,
    DocumentNotReadyForBriefError,
    LawyerPreparationBrief,
)
from app.brief.pdf_exporter import generate_brief_pdf
from app.brief.repository import BriefRepository, get_brief_repository
from app.brief.validation import (
    sanitize_neutral_text,
    validate_brief_title,
)
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
from app.evidence.validators import EvidenceValidator
from app.extraction.repository import (
    ExtractionRepository,
    get_extraction_repository,
)
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)
from app.qa.repository import QARepository, get_qa_repository
from app.reasoning.gateway import ReasoningGateway, get_reasoning_gateway
from app.reasoning.models import BriefReasoningRequest
from app.trust.classifier import TrustClassifier
from app.trust.models import SafetyStatus, TrustTier

logger = logging.getLogger(__name__)

STANDARD_DISCLAIMER = (
    "IMPORTANT NOTICE: This preparation brief is an evidence-grounded aid designed "
    "to help you prepare for a consultation with a qualified legal professional. "
    "It does NOT constitute legal advice, a legal opinion, or an enforceability "
    "prediction. Always consult a licensed attorney in your jurisdiction for "
    "specific legal counsel."
)


class BriefService:
    """Coordinates generation, validation, sanitization, and export of lawyer briefs."""

    def __init__(
        self,
        brief_repository: BriefRepository | None = None,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
        qa_repository: QARepository | None = None,
        reasoning_gateway: ReasoningGateway | None = None,
        evidence_validator: EvidenceValidator | None = None,
        trust_classifier: TrustClassifier | None = None,
    ) -> None:
        self._brief_repo = brief_repository or get_brief_repository()
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or get_extraction_repository()
        self._qa_repo = qa_repository or get_qa_repository()
        self._reasoning_gateway = reasoning_gateway or get_reasoning_gateway()
        self._evidence_validator = evidence_validator or EvidenceValidator()
        self._trust_classifier = trust_classifier or TrustClassifier()

    def generate_brief(
        self,
        document_id: str,
        user_id: str,
        title: str | None = None,
    ) -> LawyerPreparationBrief:
        """Assemble a complete Lawyer Preparation Brief for an owned document."""
        # 1. Verify document ownership
        doc = self._doc_repo.get_by_id(document_id)
        if doc is None or doc.user_id != user_id:
            raise DocumentNotFoundError(
                f"Document {document_id} not found for user {user_id}"
            )

        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForBriefError(
                f"Document {document_id} is in status '{doc.status.value}', "
                f"must be READY"
            )

        # 2. Retrieve authoritative pages
        pages = self._page_repo.get_pages_by_document(document_id)
        page_texts: dict[int, str] = {p.page_number: p.text for p in pages}

        # 3. Retrieve extracted entities
        extraction = self._extraction_repo.get_understanding_by_document(document_id)
        raw_parties = extraction.parties if extraction else []

        raw_clauses = extraction.clauses if extraction else []
        raw_obligations = extraction.obligations if extraction else []
        raw_dates = extraction.dates if extraction else []
        raw_review_flags = extraction.review_flags if extraction else []

        # 4. Mechanical Evidence Validation + Trust Classification for Sections
        sections: dict[str, BriefSection] = {}

        # Section 1: Document Snapshot & Parties
        party_items: list[BriefItem] = []
        for p in raw_parties:
            trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            safety_status = SafetyStatus.UNSUPPORTED
            ev_ref = None
            if p.source_span and p.page_number in page_texts:
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=p.page_number,
                    page_end=p.page_number,
                    source_span=p.source_span,
                )
                claim = Claim.create(
                    document_id=document_id,
                    claim_text=f"Party: {p.name} ({p.role})",
                    claim_type=ClaimType.PARTY,
                    evidence=ev_ref,
                )
                res = self._evidence_validator.validate_claim(claim, page_texts)
                if res.validation_status == EvidenceValidationStatus.VALID:
                    trust_tier = TrustTier.DOCUMENT_FACT
                    safety_status = SafetyStatus.SAFE
                else:
                    trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    safety_status = SafetyStatus.UNSUPPORTED

            party_items.append(
                BriefItem(
                    id=str(uuid.uuid4()),
                    text=f"{p.name} ({p.role})",
                    title=sanitize_neutral_text(p.name),
                    content=f"Identified role: {sanitize_neutral_text(p.role)}",
                    page_start=p.page_number,
                    page_end=p.page_number,
                    source_span=p.source_span,
                    source_type=BriefSourceType.PARTY,
                    source_id=p.id,
                    evidence=ev_ref,
                    trust_tier=trust_tier,
                    safety_status=safety_status,
                )
            )

        if party_items:
            sections["parties"] = BriefSection(
                section_key="parties",
                title="Document Snapshot & Identified Parties",
                description=(
                    "Parties identified as signatories or participants in "
                    "this document."
                ),
                items=party_items,
            )

        # Section 2: Key Clauses & Rights
        clause_items: list[BriefItem] = []
        for c in raw_clauses:
            trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            safety_status = SafetyStatus.UNSUPPORTED
            ev_ref = None
            if c.source_span and c.page_start in page_texts:
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    source_span=c.source_span,
                )
                claim = Claim.create(
                    document_id=document_id,
                    claim_text=c.text[:200],
                    claim_type=ClaimType.CLAUSE,
                    evidence=ev_ref,
                )
                res = self._evidence_validator.validate_claim(claim, page_texts)
                if res.validation_status == EvidenceValidationStatus.VALID:
                    trust_tier = TrustTier.DOCUMENT_FACT
                    safety_status = SafetyStatus.SAFE
                else:
                    trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    safety_status = SafetyStatus.UNSUPPORTED

            clause_items.append(
                BriefItem(
                    id=str(uuid.uuid4()),
                    text=f"{c.clause_identifier}: {c.title}",
                    title=f"{c.clause_identifier}: {sanitize_neutral_text(c.title)}",
                    content=sanitize_neutral_text(
                        c.text[:400] + ("..." if len(c.text) > 400 else "")
                    ),
                    page_start=c.page_start,
                    page_end=c.page_end,
                    source_span=c.source_span,
                    source_type=BriefSourceType.CLAUSE,
                    source_id=c.id,
                    evidence=ev_ref,
                    trust_tier=trust_tier,
                    safety_status=safety_status,
                )
            )

        if clause_items:
            sections["clauses"] = BriefSection(
                section_key="clauses",
                title="Key Extracted Clauses & Provisions",
                description=(
                    "Substantive contract clauses extracted with evidence spans."
                ),
                items=clause_items,
            )

        # Section 3: Operational Obligations
        obligation_items: list[BriefItem] = []
        for ob in raw_obligations:
            trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            safety_status = SafetyStatus.UNSUPPORTED
            ev_ref = None
            if ob.source_span and ob.page_start in page_texts:
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=ob.page_start,
                    page_end=ob.page_end,
                    source_span=ob.source_span,
                )
                claim = Claim.create(
                    document_id=document_id,
                    claim_text=f"{ob.obligor} {ob.duty}",
                    claim_type=ClaimType.OBLIGATION,
                    evidence=ev_ref,
                )
                res = self._evidence_validator.validate_claim(claim, page_texts)
                if res.validation_status == EvidenceValidationStatus.VALID:
                    trust_tier = TrustTier.DOCUMENT_FACT
                    safety_status = SafetyStatus.SAFE
                else:
                    trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    safety_status = SafetyStatus.UNSUPPORTED

            deadline_text = f" (Deadline: {ob.deadline})" if ob.deadline else ""
            trigger_text = f" (Trigger: {ob.trigger})" if ob.trigger else ""
            obligation_items.append(
                BriefItem(
                    id=str(uuid.uuid4()),
                    text=f"{ob.obligor}: {ob.duty}",
                    title=f"{sanitize_neutral_text(ob.obligor)} Duty",
                    content=f"{sanitize_neutral_text(ob.duty)}{deadline_text}{trigger_text}",
                    page_start=ob.page_start,
                    page_end=ob.page_end,
                    source_span=ob.source_span,
                    source_type=BriefSourceType.OBLIGATION,
                    source_id=ob.id,
                    evidence=ev_ref,
                    trust_tier=trust_tier,
                    safety_status=safety_status,
                )
            )

        if obligation_items:
            sections["obligations"] = BriefSection(
                section_key="obligations",
                title="Operational Obligations & Duties",
                description=(
                    "Affirmative duties and operational requirements "
                    "assigned to parties."
                ),
                items=obligation_items,
            )

        # Section 4: Important Dates
        date_items: list[BriefItem] = []
        for d in raw_dates:
            trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            safety_status = SafetyStatus.UNSUPPORTED
            ev_ref = None
            if d.source_span and d.page_number in page_texts:
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=d.page_number,
                    page_end=d.page_number,
                    source_span=d.source_span,
                )
                claim = Claim.create(
                    document_id=document_id,
                    claim_text=d.raw_text,
                    claim_type=ClaimType.DATE,
                    evidence=ev_ref,
                )
                res = self._evidence_validator.validate_claim(claim, page_texts)
                if res.validation_status == EvidenceValidationStatus.VALID:
                    trust_tier = TrustTier.DOCUMENT_FACT
                    safety_status = SafetyStatus.SAFE
                else:
                    trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    safety_status = SafetyStatus.UNSUPPORTED

            date_val = d.normalized_date or d.raw_text
            date_items.append(
                BriefItem(
                    id=str(uuid.uuid4()),
                    text=f"{d.date_type}: {date_val}",
                    title=f"{d.date_type.replace('_', ' ').title()}: {date_val}",
                    content=sanitize_neutral_text(d.description or d.raw_text),
                    page_start=d.page_number,
                    page_end=d.page_number,
                    source_span=d.source_span,
                    source_type=BriefSourceType.DATE,
                    source_id=d.id,
                    evidence=ev_ref,
                    trust_tier=trust_tier,
                    safety_status=safety_status,
                )
            )

        if date_items:
            sections["dates"] = BriefSection(
                section_key="dates",
                title="Important Dates & Milestones",
                description=(
                    "Extracted milestone dates, effective dates, and notice deadlines."
                ),
                items=date_items,
            )

        # Section 5: Areas for Professional Review
        flag_items: list[BriefItem] = []
        for f in raw_review_flags:
            trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
            safety_status = SafetyStatus.REVIEW_REQUIRED
            ev_ref = None
            if f.source_span and f.page_start in page_texts:
                ev_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=f.page_start,
                    page_end=f.page_end,
                    source_span=f.source_span,
                )

            flag_items.append(
                BriefItem(
                    id=str(uuid.uuid4()),
                    text=f"[{f.severity.upper()}] {f.title}",
                    title=f"[{f.severity.upper()}] {sanitize_neutral_text(f.title)}",
                    content=sanitize_neutral_text(f.description),
                    page_start=f.page_start,
                    page_end=f.page_end,
                    source_span=f.source_span,
                    source_type=BriefSourceType.REVIEW_AREA,
                    source_id=f.id,
                    evidence=ev_ref,
                    trust_tier=trust_tier,
                    safety_status=safety_status,
                    category=f.severity,
                )
            )

        if flag_items:
            sections["review_areas"] = BriefSection(
                section_key="review_areas",
                title="Areas for Professional Review",
                description=(
                    "Clauses and terms flagged for legal attention or clarification."
                ),
                items=flag_items,
            )

        # 5. Extract Q&A Findings
        qa_findings: list[dict[str, Any]] = []
        qa_items: list[BriefItem] = []
        try:
            messages = self._qa_repo.get_messages_by_document(document_id, user_id)
            for msg in messages:
                if msg.claims:
                    qa_findings.append(
                        {
                            "question": msg.question_text,
                            "answer": msg.answer_text,
                            "requires_professional_review": msg.trust_tier
                            == TrustTier.PROFESSIONAL_REVIEW_NEEDED,
                        }
                    )
                    first_claim = msg.claims[0] if msg.claims else None
                    first_ev = first_claim.evidence if first_claim else None
                    qa_title = (
                        f"Q&A Finding: {sanitize_neutral_text(msg.question_text)}"
                    )
                    qa_items.append(
                        BriefItem(
                            id=str(uuid.uuid4()),
                            text=f"Q&A: {msg.question_text}",
                            title=qa_title,
                            content=sanitize_neutral_text(msg.answer_text[:300]),
                            page_start=first_ev.page_start if first_ev else None,
                            page_end=first_ev.page_end if first_ev else None,
                            source_span=first_ev.source_span if first_ev else None,
                            source_type=BriefSourceType.QA_FINDING,
                            source_id=msg.id,
                            trust_tier=msg.trust_tier,
                            safety_status=msg.safety_status,
                        )
                    )
        except Exception as e:
            logger.warning("Could not load QA sessions for brief: %s", e)

        if qa_items:
            sections["qa_findings"] = BriefSection(
                section_key="qa_findings",
                title="Relevant Q&A Findings",
                description=(
                    "Grounded answers previously generated during document Q&A."
                ),
                items=qa_items[:5],
            )

        # 6. Synthesize Reasoning Questions via Reasoning Gateway
        reasoning_req = BriefReasoningRequest(
            document_id=document_id,
            parties=[{"name": p.name, "role": p.role} for p in raw_parties],
            clauses=[
                {
                    "category": c.category,
                    "clause_identifier": c.clause_identifier,
                    "title": c.title,
                }
                for c in raw_clauses
            ],
            obligations=[
                {"obligor": o.obligor, "duty": o.duty, "deadline": o.deadline}
                for o in raw_obligations
            ],
            dates=[
                {
                    "date_type": d.date_type,
                    "raw_text": d.raw_text,
                    "normalized_date": d.normalized_date,
                }
                for d in raw_dates
            ],
            review_flags=[
                {
                    "flag_type": f.flag_type,
                    "title": f.title,
                    "severity": f.severity,
                    "related_clause_identifier": getattr(f, "related_clause_id", None),
                }
                for f in raw_review_flags
            ],
            qa_findings=qa_findings,
            metadata={"filename": doc.filename, "title": doc.filename},
        )

        reasoning_res = self._reasoning_gateway.generate_brief_questions(reasoning_req)

        # 7. Sanitize generated questions and lists
        clean_questions: list[BriefQuestion] = []
        for q in reasoning_res.questions:
            clean_q = sanitize_neutral_text(q.question)
            clean_rat = sanitize_neutral_text(q.rationale) if q.rationale else None
            clean_questions.append(
                BriefQuestion(
                    question=clean_q,
                    category=q.category,
                    rationale=clean_rat,
                    related_clause_id=q.related_clause_id,
                )
            )

        clean_facts = [sanitize_neutral_text(f) for f in reasoning_res.facts_to_confirm]
        clean_docs = [
            sanitize_neutral_text(d) for d in reasoning_res.documents_to_bring
        ]
        clean_open_q = [
            sanitize_neutral_text(oq) for oq in reasoning_res.open_questions
        ]

        # 8. Compute Completeness Score
        total_factors = 5
        present_factors = 0
        if raw_parties:
            present_factors += 1
        if raw_clauses:
            present_factors += 1
        if raw_obligations:
            present_factors += 1
        if raw_dates:
            present_factors += 1
        if clean_questions:
            present_factors += 1
        completeness_score = round(present_factors / total_factors, 2)

        # 9. Formulate Executive Summary
        exec_summary = (
            f"This preparation brief summarizes key factual terms, rights, and "
            f"operational obligations identified in '{doc.filename}'. It outlines "
            f"{len(clean_questions)} focused questions and {len(flag_items)} review "
            f"areas to guide consultation with a qualified legal professional."
        )

        # 10. Construct Domain Model
        brief_title = validate_brief_title(
            title or f"Lawyer Preparation Brief — {doc.filename}"
        )
        brief = LawyerPreparationBrief(
            id=str(uuid.uuid4()),
            document_id=document_id,
            title=brief_title,
            situation_summary=exec_summary,
            sections=sections,
            questions_for_lawyer=clean_questions,
            facts_to_confirm=clean_facts,
            documents_to_bring=clean_docs,
            open_questions=clean_open_q,
            completeness_score=completeness_score,
            disclaimer=STANDARD_DISCLAIMER,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )

        # 11. Persist in Repository
        self._brief_repo.save_brief(brief, user_id)
        logger.info(
            "Successfully assembled and saved lawyer preparation brief %s for doc %s",
            brief.id,
            document_id,
        )
        return brief

    def get_brief_by_document(
        self, document_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        """Retrieve existing brief for a document after checking ownership."""
        doc = self._doc_repo.get_by_id(document_id)
        if doc is None or doc.user_id != user_id:
            raise DocumentNotFoundError(
                f"Document {document_id} not found for user {user_id}"
            )
        return self._brief_repo.get_latest_brief_by_document(document_id, user_id)

    def get_brief_by_id(self, brief_id: str, user_id: str) -> LawyerPreparationBrief:
        """Retrieve brief by ID after checking tenant document ownership."""
        brief = self._brief_repo.get_brief_by_id(brief_id, user_id)
        if brief is None:
            raise BriefNotFoundError(f"Preparation brief {brief_id} not found")
        return brief

    def delete_brief(self, brief_id: str, user_id: str) -> bool:
        """Delete brief by ID after checking tenant document ownership."""
        deleted = self._brief_repo.delete_brief(brief_id, user_id)
        if not deleted:
            raise BriefNotFoundError(f"Preparation brief {brief_id} not found")
        return True

    def export_brief_pdf(self, brief_id: str, user_id: str) -> bytes:
        """Generate in-memory PDF export for a brief."""
        brief = self.get_brief_by_id(brief_id, user_id)
        return generate_brief_pdf(brief)


_brief_service: BriefService | None = None


def get_brief_service() -> BriefService:
    """Return singleton or configured instance of BriefService."""
    global _brief_service
    if _brief_service is None:
        _brief_service = BriefService()
    return _brief_service
