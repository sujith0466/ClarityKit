import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import EvidenceReference
from app.trust.models import SafetyStatus, TrustTier


class QAError(Exception):
    """Base exception for Q&A operations."""

    pass


class DocumentNotFoundError(QAError):
    """Raised when the target document does not exist or user lacks ownership."""

    pass


class DocumentNotReadyForQAError(QAError):
    """Raised when the document has not finished processing/indexing."""

    pass


class InvalidQuestionError(QAError):
    """Raised when the user question is invalid or exceeds bounds."""

    pass


class QASessionNotFoundError(QAError):
    """Raised when a requested Q&A session is not found or not owned."""

    pass


class RetrievalSufficiency(str, Enum):
    """Sufficiency classification of retrieved context for answering a query."""

    SUFFICIENT = "sufficient"
    WEAK = "weak"
    NONE = "none"


@dataclass
class AnswerClaim:
    """Individual assertion with evidence and trust classification."""

    id: str
    claim_text: str
    claim_type: str
    evidence: EvidenceReference | None = None
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT
    safety_status: SafetyStatus = SafetyStatus.SAFE
    is_valid: bool = True
    validation_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
            "is_valid": self.is_valid,
            "validation_reason": self.validation_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerClaim":
        ev_data = data.get("evidence")
        ev_ref = (
            EvidenceReference(
                document_id=ev_data["document_id"],
                page_start=ev_data.get("page_start", 1),
                page_end=ev_data.get("page_end", 1),
                source_span=ev_data.get("source_span", ""),
                section=ev_data.get("section"),
                clause_id=ev_data.get("clause_id"),
            )
            if ev_data
            else None
        )

        tier_str = data.get("trust_tier", "DOCUMENT_FACT")
        safety_str = data.get("safety_status", "SAFE")

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            claim_text=data.get("claim_text", ""),
            claim_type=data.get("claim_type", "general_fact"),
            evidence=ev_ref,
            trust_tier=TrustTier(tier_str)
            if tier_str in [t.value for t in TrustTier]
            else TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus(safety_str)
            if safety_str in [s.value for s in SafetyStatus]
            else SafetyStatus.SAFE,
            is_valid=data.get("is_valid", True),
            validation_reason=data.get("validation_reason", ""),
        )


@dataclass
class QAMessage:
    """A single Q&A exchange within a session."""

    id: str
    session_id: str
    document_id: str
    question_text: str
    answer_text: str
    trust_tier: TrustTier
    safety_status: SafetyStatus
    evidence_coverage: float
    is_grounded: bool
    claims: list[AnswerClaim] = field(default_factory=list)
    evidence_references: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "document_id": self.document_id,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
            "evidence_coverage": self.evidence_coverage,
            "is_grounded": self.is_grounded,
            "claims": [c.to_dict() for c in self.claims],
            "evidence_references": self.evidence_references,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QAMessage":
        tier_str = data.get("trust_tier", "DOCUMENT_FACT")
        safety_str = data.get("safety_status", "SAFE")

        claims_raw = data.get("claims", [])
        claims = [
            AnswerClaim.from_dict(c) if isinstance(c, dict) else c for c in claims_raw
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            session_id=data.get("session_id", ""),
            document_id=data.get("document_id", ""),
            question_text=data.get("question_text", ""),
            answer_text=data.get("answer_text", ""),
            trust_tier=TrustTier(tier_str)
            if tier_str in [t.value for t in TrustTier]
            else TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus(safety_str)
            if safety_str in [s.value for s in SafetyStatus]
            else SafetyStatus.SAFE,
            evidence_coverage=float(data.get("evidence_coverage", 0.0)),
            is_grounded=bool(data.get("is_grounded", False)),
            claims=claims,
            evidence_references=data.get("evidence_references", []),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
        )


@dataclass
class QASession:
    """Document-scoped interactive Q&A session."""

    id: str
    document_id: str
    title: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    messages: list[QAMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QASession":
        messages_raw = data.get("messages", [])
        messages = [
            QAMessage.from_dict(m) if isinstance(m, dict) else m for m in messages_raw
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            document_id=data.get("document_id", ""),
            title=data.get("title", "Document Q&A Session"),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
            messages=messages,
        )
