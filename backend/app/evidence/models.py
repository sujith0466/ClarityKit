import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EvidenceError(Exception):
    """Base exception for Evidence Engine operations."""

    pass


class DocumentNotFoundError(EvidenceError):
    """Raised when the requested document does not exist or is not accessible."""

    pass


class DocumentNotReadyForEvidenceError(EvidenceError):
    """Raised when evidence validation is requested on an unready document."""

    pass


class InvalidEvidenceInputError(EvidenceError):
    """Raised when input parameters are invalid or out of bounds."""

    pass


class EvidenceValidationStatus(str, Enum):
    """Mechanical citation validation status."""

    VALID = "VALID"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


class EvidenceMatchType(str, Enum):
    """Type of mechanical text match achieved."""

    EXACT = "exact"
    NORMALIZED_WHITESPACE = "normalized_whitespace"
    CROSS_PAGE = "cross_page"
    UNMATCHED = "unmatched"


class ClaimType(str, Enum):
    """Type of legal claim or extracted fact."""

    PARTY = "party"
    CLAUSE = "clause"
    OBLIGATION = "obligation"
    DATE = "date"
    REVIEW_FLAG = "review_flag"
    GENERAL_FACT = "general_fact"


@dataclass
class EvidenceReference:
    """Provenance citation and mechanical verification details for a claim."""

    document_id: str
    page_start: int
    page_end: int
    source_span: str
    section: str | None = None
    clause_id: str | None = None
    source_text: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    match_type: EvidenceMatchType = EvidenceMatchType.UNMATCHED
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNVERIFIED
    validation_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "section": self.section,
            "clause_id": self.clause_id,
            "source_text": self.source_text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "match_type": self.match_type.value,
            "validation_status": self.validation_status.value,
            "validation_reason": self.validation_reason,
        }


@dataclass
class Claim:
    """Document-specific claim or structured legal fact linked to evidence."""

    id: str
    document_id: str
    claim_text: str
    claim_type: ClaimType
    entity_id: str | None = None
    evidence: EvidenceReference | None = None
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNVERIFIED

    @classmethod
    def create(
        cls,
        document_id: str,
        claim_text: str,
        claim_type: ClaimType,
        evidence: EvidenceReference | None = None,
        entity_id: str | None = None,
        claim_id: str | None = None,
    ) -> "Claim":
        clean_text = claim_text.strip()
        if not clean_text:
            raise InvalidEvidenceInputError("Claim text cannot be empty.")

        status = (
            evidence.validation_status
            if evidence is not None
            else EvidenceValidationStatus.INVALID
        )

        return cls(
            id=claim_id or str(uuid.uuid4()),
            document_id=document_id,
            claim_text=clean_text,
            claim_type=claim_type,
            entity_id=entity_id,
            evidence=evidence,
            validation_status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "entity_id": self.entity_id,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "validation_status": self.validation_status.value,
        }


@dataclass
class EvidenceCoverage:
    """Deterministic coverage metrics for document claims."""

    total_claims: int
    valid_claims: int
    invalid_claims: int
    unverified_claims: int
    coverage_ratio: float
    is_fully_covered: bool

    @property
    def coverage_percentage(self) -> float:
        return round(self.coverage_ratio * 100, 2)

    @classmethod
    def calculate(cls, claims: list[Claim]) -> "EvidenceCoverage":
        total = len(claims)
        if total == 0:
            return cls(
                total_claims=0,
                valid_claims=0,
                invalid_claims=0,
                unverified_claims=0,
                coverage_ratio=0.0,
                is_fully_covered=False,
            )

        valid = sum(
            1
            for c in claims
            if c.validation_status == EvidenceValidationStatus.VALID
            and c.evidence is not None
            and c.evidence.validation_status == EvidenceValidationStatus.VALID
        )
        invalid = sum(
            1
            for c in claims
            if c.validation_status == EvidenceValidationStatus.INVALID
            or c.evidence is None
            or c.evidence.validation_status == EvidenceValidationStatus.INVALID
        )
        unverified = total - valid - invalid

        # Exact decimal ratio (rounded to 4 decimal places without upward inflation)
        ratio = round(valid / total, 4)
        is_full = total > 0 and valid == total

        return cls(
            total_claims=total,
            valid_claims=valid,
            invalid_claims=invalid,
            unverified_claims=unverified,
            coverage_ratio=ratio,
            is_fully_covered=is_full,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_claims": self.total_claims,
            "valid_claims": self.valid_claims,
            "invalid_claims": self.invalid_claims,
            "unverified_claims": self.unverified_claims,
            "coverage_ratio": self.coverage_ratio,
            "coverage_percentage": self.coverage_percentage,
            "is_fully_covered": self.is_fully_covered,
        }


@dataclass
class DocumentEvidenceReport:
    """Complete evidence verification report for a document."""

    document_id: str
    claims: list[Claim]
    coverage: EvidenceCoverage
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    disclaimer: str = (
        "Citation validity indicates that the referenced text span "
        "exists at the claimed document location. "
        "It does not guarantee semantic or legal correctness, "
        "enforceability, or constitute legal advice."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "claims": [c.to_dict() for c in self.claims],
            "coverage": self.coverage.to_dict(),
            "generated_at": self.generated_at,
            "disclaimer": self.disclaimer,
        }
