"""Domain models for Lawyer-Preparation Briefs."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import EvidenceReference
from app.trust.models import SafetyStatus, TrustTier


class BriefSourceType(str, Enum):
    """Source origin of a brief item."""

    PARTY = "PARTY"
    CLAUSE = "CLAUSE"
    OBLIGATION = "OBLIGATION"
    DATE = "DATE"
    REVIEW_AREA = "REVIEW_AREA"
    QA_FINDING = "QA_FINDING"
    EXTRACTION = "EXTRACTION"
    EVIDENCE = "EVIDENCE"
    GROUNDED_QA = "GROUNDED_QA"
    USER_INPUT = "USER_INPUT"
    SYNTHESIS = "SYNTHESIS"


class BriefError(Exception):
    """Base exception for preparation brief operations."""

    pass


class DocumentNotFoundError(BriefError):
    """Raised when a referenced document cannot be found or is not accessible."""

    pass


class BriefNotFoundError(BriefError):
    """Raised when a requested brief is not found or inaccessible."""

    pass


class DocumentNotReadyForBriefError(BriefError):
    """Raised when a document is not ready for brief generation."""

    pass


class InvalidBriefStateError(BriefError):
    """Raised when brief input or state is invalid."""

    pass


@dataclass
class BriefItem:
    """A single atomic item in a preparation brief with traceable provenance."""

    id: str
    text: str
    source_type: BriefSourceType
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT
    safety_status: SafetyStatus = SafetyStatus.SAFE
    title: str | None = None
    content: str | None = None
    category: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_span: str | None = None
    source_id: str | None = None
    evidence: EvidenceReference | None = None
    is_valid: bool = True
    validation_reason: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "title": self.title or self.text,
            "content": self.content or self.text,
            "source_type": self.source_type.value,
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
            "category": self.category,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "source_id": self.source_id,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "is_valid": self.is_valid,
            "validation_reason": self.validation_reason,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefItem":
        ev_data = data.get("evidence")
        ev_ref = None
        if ev_data:
            ev_ref = EvidenceReference(
                document_id=ev_data.get("document_id", ""),
                page_start=ev_data.get("page_start", 1),
                page_end=ev_data.get("page_end", 1),
                source_span=ev_data.get("source_span", ""),
                section=ev_data.get("section"),
                clause_id=ev_data.get("clause_id"),
                source_text=ev_data.get("source_text"),
                char_start=ev_data.get("char_start"),
                char_end=ev_data.get("char_end"),
            )

        return cls(
            id=data["id"],
            text=data.get("text", data.get("title", "")),
            title=data.get("title"),
            content=data.get("content"),
            source_type=BriefSourceType(data.get("source_type", "SYNTHESIS")),
            trust_tier=TrustTier(data.get("trust_tier", "DOCUMENT_FACT")),
            safety_status=SafetyStatus(data.get("safety_status", "SAFE")),
            category=data.get("category"),
            page_start=data.get("page_start"),
            page_end=data.get("page_end"),
            source_span=data.get("source_span"),
            source_id=data.get("source_id"),
            evidence=ev_ref,
            is_valid=data.get("is_valid", True),
            validation_reason=data.get("validation_reason"),
            notes=data.get("notes"),
        )


@dataclass
class BriefSection:
    """A logical section within the preparation brief."""

    section_key: str
    title: str
    description: str
    items: list[BriefItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_key": self.section_key,
            "title": self.title,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefSection":
        return cls(
            section_key=data.get("section_key", data.get("id", "")),
            title=data["title"],
            description=data.get("description", ""),
            items=[BriefItem.from_dict(it) for it in data.get("items", [])],
        )


BRIEF_DEFAULT_DISCLAIMER = (
    "IMPORTANT NOTICE: This preparation brief is an evidence-grounded aid designed "
    "to help you prepare for a consultation with a qualified legal professional. "
    "It does NOT constitute legal advice, a legal opinion, or an enforceability "
    "prediction. Always consult a licensed attorney in your jurisdiction for "
    "specific legal counsel."
)


@dataclass
class BriefQuestion:
    """Structured question for consulting a legal professional."""

    question: str
    category: str = "general"
    rationale: str | None = None
    related_clause_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "category": self.category,
            "rationale": self.rationale,
            "related_clause_id": self.related_clause_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefQuestion":
        return cls(
            question=data["question"],
            category=data.get("category", "general"),
            rationale=data.get("rationale"),
            related_clause_id=data.get("related_clause_id"),
        )


@dataclass
class LawyerPreparationBrief:
    """Complete preparation brief aggregate root."""

    id: str
    document_id: str
    title: str
    situation_summary: str
    sections: dict[str, BriefSection]
    questions_for_lawyer: list[BriefQuestion] = field(default_factory=list)
    facts_to_confirm: list[str] = field(default_factory=list)
    documents_to_bring: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    completeness_score: float = 1.0
    evidence_references: list[dict[str, Any]] = field(default_factory=list)
    is_grounded: bool = True
    disclaimer: str = BRIEF_DEFAULT_DISCLAIMER
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "title": self.title,
            "situation_summary": self.situation_summary,
            "executive_summary": self.situation_summary,
            "disclaimer": self.disclaimer,
            "sections": {k: sec.to_dict() for k, sec in self.sections.items()},
            "questions_for_lawyer": [q.to_dict() for q in self.questions_for_lawyer],
            "facts_to_confirm": self.facts_to_confirm,
            "documents_to_bring": self.documents_to_bring,
            "open_questions": self.open_questions,
            "completeness_score": self.completeness_score,
            "evidence_references": self.evidence_references,
            "is_grounded": self.is_grounded,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LawyerPreparationBrief":
        raw_sections = data.get("sections", {})
        if isinstance(raw_sections, list):
            sections_dict = {
                sec["section_key"]: BriefSection.from_dict(sec) for sec in raw_sections
            }
        else:
            sections_dict = {
                k: BriefSection.from_dict(v) for k, v in raw_sections.items()
            }

        raw_questions = data.get("questions_for_lawyer", [])
        questions = [
            BriefQuestion.from_dict(q) if isinstance(q, dict) else q
            for q in raw_questions
        ]

        return cls(
            id=data["id"],
            document_id=data["document_id"],
            title=data.get("title", "Lawyer-Preparation Brief"),
            situation_summary=data.get(
                "situation_summary", data.get("executive_summary", "")
            ),
            disclaimer=data.get("disclaimer", BRIEF_DEFAULT_DISCLAIMER),
            sections=sections_dict,
            questions_for_lawyer=questions,
            facts_to_confirm=data.get("facts_to_confirm", []),
            documents_to_bring=data.get("documents_to_bring", []),
            open_questions=data.get("open_questions", []),
            completeness_score=float(data.get("completeness_score", 1.0)),
            evidence_references=data.get("evidence_references", []),
            is_grounded=data.get("is_grounded", True),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )

    @classmethod
    def create_empty(
        cls, document_id: str, title: str | None = None
    ) -> "LawyerPreparationBrief":
        now = datetime.now(UTC).isoformat()
        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            title=title or "Lawyer-Preparation Brief",
            situation_summary="",
            sections={},
            questions_for_lawyer=[],
            facts_to_confirm=[],
            documents_to_bring=[],
            open_questions=[],
            completeness_score=0.0,
            evidence_references=[],
            is_grounded=True,
            disclaimer=BRIEF_DEFAULT_DISCLAIMER,
            created_at=now,
            updated_at=now,
        )
