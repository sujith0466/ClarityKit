"""Domain models and data structures for Document Version Diff (Phase 14)."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import EvidenceValidationStatus
from app.trust.models import SafetyStatus, TrustTier


class VersionDiffError(Exception):
    """Base exception for version diff errors."""


class VersionDiffNotFoundError(VersionDiffError):
    """Raised when a version diff or document is not found or unauthorized (404)."""


class InvalidVersionDiffInputError(VersionDiffError):
    """Raised when version diff parameters violate constraints."""


class DocumentNotReadyForVersionDiffError(VersionDiffError):
    """Raised when a document is not in 'ready' status for version diffing."""


class VersionDiffClassification(str, Enum):
    """Domain classifications for version comparison deltas."""

    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"
    POTENTIAL_CHANGE = "POTENTIAL_CHANGE"
    UNRESOLVED = "UNRESOLVED"


class VersionDiffCategory(str, Enum):
    """Categories of version diff changes."""

    CLAUSE = "CLAUSE"
    PARTIES = "PARTIES"
    DATES = "DATES"
    OBLIGATIONS = "OBLIGATIONS"
    NOTICE = "NOTICE"
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"


@dataclass
class VersionEvidenceRef:
    """Evidence citation associated with a specific document version."""

    document_id: str
    version_label: str  # "v1" or "v2"
    document_title: str
    page_start: int
    page_end: int
    source_span: str
    exact_quote: str = ""
    section: str = ""
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNVERIFIED
    char_start: int | None = None
    char_end: int | None = None
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "version_label": self.version_label,
            "document_title": self.document_title,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "exact_quote": self.exact_quote,
            "section": self.section,
            "validation_status": self.validation_status.value,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "trust_tier": self.trust_tier.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionEvidenceRef":
        return cls(
            document_id=data["document_id"],
            version_label=data.get("version_label", "v1"),
            document_title=data.get("document_title", ""),
            page_start=int(data.get("page_start", 1)),
            page_end=int(data.get("page_end", 1)),
            source_span=data.get("source_span", ""),
            exact_quote=data.get("exact_quote", ""),
            section=data.get("section", ""),
            validation_status=EvidenceValidationStatus(
                data.get("validation_status", EvidenceValidationStatus.UNVERIFIED.value)
            ),
            char_start=data.get("char_start"),
            char_end=data.get("char_end"),
            trust_tier=TrustTier(data.get("trust_tier", TrustTier.DOCUMENT_FACT.value)),
        )


@dataclass
class VersionDiffFinding:
    """Individual delta finding between Version 1 and Version 2."""

    id: str
    category: VersionDiffCategory
    title: str
    description: str
    classification: VersionDiffClassification
    v1_evidence: list[VersionEvidenceRef] = field(default_factory=list)
    v2_evidence: list[VersionEvidenceRef] = field(default_factory=list)
    lawyer_questions: list[str] = field(default_factory=list)
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT
    safety_status: SafetyStatus = SafetyStatus.SAFE

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "classification": self.classification.value,
            "v1_evidence": [e.to_dict() for e in self.v1_evidence],
            "v2_evidence": [e.to_dict() for e in self.v2_evidence],
            "lawyer_questions": list(self.lawyer_questions),
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionDiffFinding":
        return cls(
            id=data["id"],
            category=VersionDiffCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            classification=VersionDiffClassification(data["classification"]),
            v1_evidence=[
                VersionEvidenceRef.from_dict(e) for e in data.get("v1_evidence", [])
            ],
            v2_evidence=[
                VersionEvidenceRef.from_dict(e) for e in data.get("v2_evidence", [])
            ],
            lawyer_questions=list(data.get("lawyer_questions", [])),
            trust_tier=TrustTier(data.get("trust_tier", TrustTier.DOCUMENT_FACT.value)),
            safety_status=SafetyStatus(
                data.get("safety_status", SafetyStatus.SAFE.value)
            ),
        )


@dataclass
class VersionDocumentRef:
    """Metadata for a document participating in a version diff."""

    id: str
    filename: str
    version_label: str  # "v1" / "Base" or "v2" / "Revised"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionDocumentRef":
        return cls(
            id=data["id"],
            filename=data["filename"],
            version_label=data.get("version_label", ""),
        )


@dataclass
class VersionDiffSummary:
    """Summary metrics for a version diff."""

    total_findings: int = 0
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0
    potential_change_count: int = 0
    unresolved_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionDiffSummary":
        return cls(
            total_findings=int(data.get("total_findings", 0)),
            added_count=int(data.get("added_count", 0)),
            removed_count=int(data.get("removed_count", 0)),
            modified_count=int(data.get("modified_count", 0)),
            unchanged_count=int(data.get("unchanged_count", 0)),
            potential_change_count=int(data.get("potential_change_count", 0)),
            unresolved_count=int(data.get("unresolved_count", 0)),
        )

    @classmethod
    def from_findings(cls, findings: list[VersionDiffFinding]) -> "VersionDiffSummary":
        return cls(
            total_findings=len(findings),
            added_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.ADDED
            ),
            removed_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.REMOVED
            ),
            modified_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.MODIFIED
            ),
            unchanged_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.UNCHANGED
            ),
            potential_change_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.POTENTIAL_CHANGE
            ),
            unresolved_count=sum(
                1
                for f in findings
                if f.classification == VersionDiffClassification.UNRESOLVED
            ),
        )


@dataclass
class DocumentVersionDiff:
    """Top-level aggregate representation of a Version 1 vs Version 2 diff."""

    id: str
    user_id: str
    title: str
    v1_document: VersionDocumentRef
    v2_document: VersionDocumentRef
    findings: list[VersionDiffFinding] = field(default_factory=list)
    summary: VersionDiffSummary = field(default_factory=VersionDiffSummary)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "v1_document": self.v1_document.to_dict(),
            "v2_document": self.v2_document.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentVersionDiff":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            title=data.get("title", "Version Diff"),
            v1_document=VersionDocumentRef.from_dict(data["v1_document"]),
            v2_document=VersionDocumentRef.from_dict(data["v2_document"]),
            findings=[
                VersionDiffFinding.from_dict(f) for f in data.get("findings", [])
            ],
            summary=VersionDiffSummary.from_dict(data.get("summary", {})),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )
