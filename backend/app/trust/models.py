import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import ClaimType, EvidenceReference


class TrustError(Exception):
    """Base exception for Trust & Safety operations."""

    pass


class DocumentNotFoundError(TrustError):
    """Raised when the requested document does not exist or is not accessible."""

    pass


class DocumentNotReadyForTrustError(TrustError):
    """Raised when trust assessment is requested on an unready document."""

    pass


class InvalidTrustInputError(TrustError):
    """Raised when input parameters are invalid or out of bounds."""

    pass


class TrustTier(str, Enum):
    """Four-tier trust classification for document claims and legal concepts."""

    DOCUMENT_FACT = "DOCUMENT_FACT"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    INTERPRETATION = "INTERPRETATION"
    PROFESSIONAL_REVIEW_NEEDED = "PROFESSIONAL_REVIEW_NEEDED"


class SafetyStatus(str, Enum):
    """Machine-readable safety boundary status."""

    SAFE = "SAFE"
    LIMITED = "LIMITED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class LimitationType(str, Enum):
    """Structured limitation indicators explaining why a claim is bounded."""

    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    CROSS_DOCUMENT_EVIDENCE = "CROSS_DOCUMENT_EVIDENCE"
    MISSING_JURISDICTION = "MISSING_JURISDICTION"
    MISSING_FACTS = "MISSING_FACTS"
    CURRENT_LAW_REQUIRED = "CURRENT_LAW_REQUIRED"
    AMBIGUOUS_LANGUAGE = "AMBIGUOUS_LANGUAGE"
    OUTSIDE_DOCUMENT = "OUTSIDE_DOCUMENT"
    LEGAL_ENFORCEABILITY = "LEGAL_ENFORCEABILITY"
    PROFESSIONAL_JUDGMENT = "PROFESSIONAL_JUDGMENT"


@dataclass
class TrustAssessment:
    """Safety evaluation metadata for a single legal claim."""

    claim_id: str
    trust_tier: TrustTier
    safety_status: SafetyStatus
    evidence_required: bool
    evidence_valid: bool
    professional_review_required: bool
    limitations: list[LimitationType] = field(default_factory=list)
    reasoning_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
            "evidence_required": self.evidence_required,
            "evidence_valid": self.evidence_valid,
            "professional_review_required": self.professional_review_required,
            "limitations": [lim.value for lim in self.limitations],
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrustAssessment":
        return cls(
            claim_id=str(data["claim_id"]),
            trust_tier=TrustTier(data["trust_tier"]),
            safety_status=SafetyStatus(data["safety_status"]),
            evidence_required=bool(data.get("evidence_required", True)),
            evidence_valid=bool(data.get("evidence_valid", False)),
            professional_review_required=bool(
                data.get("professional_review_required", False)
            ),
            limitations=[LimitationType(lim) for lim in data.get("limitations", [])],
            reasoning_summary=str(data.get("reasoning_summary", "")),
        )


@dataclass
class AssessedClaim:
    """A claim fully evaluated by both Evidence and Trust & Safety layers."""

    id: str
    document_id: str
    claim_text: str
    claim_type: ClaimType
    trust_assessment: TrustAssessment
    evidence: EvidenceReference | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "trust_assessment": self.trust_assessment.to_dict(),
            "evidence": [self.evidence.to_dict()] if self.evidence else [],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssessedClaim":
        ev_list = data.get("evidence", [])
        evidence_ref: EvidenceReference | None = None
        if ev_list and isinstance(ev_list, list) and len(ev_list) > 0:
            e = ev_list[0]
            evidence_ref = EvidenceReference(
                document_id=str(e["document_id"]),
                page_start=int(e["page_start"]),
                page_end=int(e["page_end"]),
                source_span=str(e["source_span"]),
                section=e.get("section"),
                clause_id=e.get("clause_id"),
                source_text=e.get("source_text"),
                char_start=e.get("char_start"),
                char_end=e.get("char_end"),
                match_type=e.get("match_type", "unmatched"),
                validation_status=e.get("validation_status", "UNVERIFIED"),
                validation_reason=e.get("validation_reason"),
            )

        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            document_id=str(data["document_id"]),
            claim_text=str(data["claim_text"]),
            claim_type=ClaimType(data["claim_type"]),
            trust_assessment=TrustAssessment.from_dict(data["trust_assessment"]),
            evidence=evidence_ref,
            created_at=str(data.get("created_at", datetime.now(UTC).isoformat())),
        )


@dataclass
class DocumentTrustReport:
    """Aggregated trust and safety evaluation for an entire legal document."""

    document_id: str
    assessed_claims: list[AssessedClaim]
    overall_safety_status: SafetyStatus
    evidence_coverage: float
    total_claims: int
    tier_counts: dict[str, int]
    limitation_counts: dict[str, int]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    disclaimer: str = (
        "Trust & Safety classifications describe how information was "
        "derived and bounded. Evidence coverage measures mechanically valid "
        "citations, not semantic accuracy, legal accuracy, enforceability, "
        "or legal advice. This platform does not provide legal advice."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "assessed_claims": [c.to_dict() for c in self.assessed_claims],
            "overall_safety_status": self.overall_safety_status.value,
            "evidence_coverage": self.evidence_coverage,
            "total_claims": self.total_claims,
            "tier_counts": self.tier_counts,
            "limitation_counts": self.limitation_counts,
            "generated_at": self.generated_at,
            "disclaimer": self.disclaimer,
        }
