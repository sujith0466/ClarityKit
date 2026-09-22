"""Domain models, enums, and schemas for Multi-Document Comparison (Phase 13)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import EvidenceValidationStatus
from app.trust.models import SafetyStatus, TrustTier


class ComparisonError(Exception):
    """Base exception for Comparison operations."""

    pass


class ComparisonNotFoundError(ComparisonError):
    """Raised when the requested comparison does not exist or is not owned."""

    pass


class InvalidComparisonInputError(ComparisonError):
    """Raised when comparison input parameters are invalid (e.g. count < 2)."""

    pass


class DocumentNotReadyForComparisonError(ComparisonError):
    """Raised when documents have not finished extraction/evidence processing."""

    pass


class ComparisonTenantMismatchError(ComparisonError):
    """Raised when a comparison includes documents across different tenants."""

    pass


class ComparisonCategory(str, Enum):
    """Factual and structural categories for cross-document comparison."""

    PARTIES = "PARTIES"
    DATES = "DATES"
    OBLIGATIONS = "OBLIGATIONS"
    TERMINATION = "TERMINATION"
    PAYMENT = "PAYMENT"
    DURATION = "DURATION"
    CLAUSE = "CLAUSE"
    DEFINITIONS = "DEFINITIONS"
    NOTICE = "NOTICE"
    OTHER = "OTHER"


class DifferenceClassification(str, Enum):
    """Domain comparison state for an item across multiple documents.

    Note: These are comparison states only, NOT Phase 8 SafetyStatus values.
    """

    MATCH = "MATCH"
    DIFFERENT = "DIFFERENT"
    PRESENT_IN_ONE_ONLY = "PRESENT_IN_ONE_ONLY"
    POTENTIAL_INCONSISTENCY = "POTENTIAL_INCONSISTENCY"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class DocumentEvidenceRef:
    """Projection referencing validated Phase 7 evidence in a specific document."""

    document_id: str
    document_title: str
    page_start: int
    page_end: int
    source_span: str
    section: str | None = None
    exact_quote: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNVERIFIED
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "section": self.section,
            "exact_quote": self.exact_quote,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "validation_status": self.validation_status.value
            if isinstance(self.validation_status, EvidenceValidationStatus)
            else str(self.validation_status),
            "trust_tier": self.trust_tier.value
            if isinstance(self.trust_tier, TrustTier)
            else str(self.trust_tier),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentEvidenceRef:
        status_raw = data.get("validation_status", "UNVERIFIED")
        try:
            status = EvidenceValidationStatus(status_raw)
        except ValueError:
            status = EvidenceValidationStatus.UNVERIFIED

        tier_raw = data.get("trust_tier", "DOCUMENT_FACT")
        try:
            tier = TrustTier(tier_raw)
        except ValueError:
            tier = TrustTier.DOCUMENT_FACT

        return cls(
            document_id=str(data["document_id"]),
            document_title=str(data.get("document_title", "Document")),
            page_start=int(data.get("page_start", 1)),
            page_end=int(data.get("page_end", 1)),
            source_span=str(data.get("source_span", "")),
            section=data.get("section"),
            exact_quote=data.get("exact_quote"),
            char_start=data.get("char_start"),
            char_end=data.get("char_end"),
            validation_status=status,
            trust_tier=tier,
        )


@dataclass
class ComparisonDocumentRef:
    """Document reference metadata in a comparison set."""

    document_id: str
    title: str
    filename: str
    page_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "filename": self.filename,
            "page_count": self.page_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComparisonDocumentRef:
        return cls(
            document_id=str(data["document_id"]),
            title=str(data.get("title", "")),
            filename=str(data.get("filename", "")),
            page_count=int(data.get("page_count", 1)),
        )


@dataclass
class ComparisonFinding:
    """A cross-document comparison finding backed by validated evidence."""

    id: str
    category: ComparisonCategory
    title: str
    description: str
    classification: DifferenceClassification
    evidence_references: list[DocumentEvidenceRef] = field(default_factory=list)
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
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "lawyer_questions": list(self.lawyer_questions),
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComparisonFinding:
        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            category=ComparisonCategory(data.get("category", "OTHER")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            classification=DifferenceClassification(
                data.get("classification", "UNRESOLVED")
            ),
            evidence_references=[
                DocumentEvidenceRef.from_dict(ref_data)
                for ref_data in data.get("evidence_references", [])
            ],
            lawyer_questions=list(data.get("lawyer_questions", [])),
            trust_tier=TrustTier(data.get("trust_tier", "DOCUMENT_FACT")),
            safety_status=SafetyStatus(data.get("safety_status", "SAFE")),
        )


@dataclass
class ComparisonSummary:
    """Aggregate metric counts for a multi-document comparison."""

    total_findings: int = 0
    match_count: int = 0
    difference_count: int = 0
    present_in_one_only_count: int = 0
    potential_inconsistency_count: int = 0
    unresolved_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "match_count": self.match_count,
            "difference_count": self.difference_count,
            "present_in_one_only_count": self.present_in_one_only_count,
            "potential_inconsistency_count": self.potential_inconsistency_count,
            "unresolved_count": self.unresolved_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComparisonSummary:
        return cls(
            total_findings=int(data.get("total_findings", 0)),
            match_count=int(data.get("match_count", 0)),
            difference_count=int(data.get("difference_count", 0)),
            present_in_one_only_count=int(data.get("present_in_one_only_count", 0)),
            potential_inconsistency_count=int(
                data.get("potential_inconsistency_count", 0)
            ),
            unresolved_count=int(data.get("unresolved_count", 0)),
        )

    @classmethod
    def compute(cls, findings: list[ComparisonFinding]) -> ComparisonSummary:
        total = len(findings)
        matches = sum(
            1 for f in findings if f.classification == DifferenceClassification.MATCH
        )
        diffs = sum(
            1
            for f in findings
            if f.classification == DifferenceClassification.DIFFERENT
        )
        present_in_one = sum(
            1
            for f in findings
            if f.classification == DifferenceClassification.PRESENT_IN_ONE_ONLY
        )
        inconsistencies = sum(
            1
            for f in findings
            if f.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
        )
        unresolved = sum(
            1
            for f in findings
            if f.classification == DifferenceClassification.UNRESOLVED
        )

        return cls(
            total_findings=total,
            match_count=matches,
            difference_count=diffs,
            present_in_one_only_count=present_in_one,
            potential_inconsistency_count=inconsistencies,
            unresolved_count=unresolved,
        )


@dataclass
class DocumentComparison:
    """Complete persisted multi-document comparison record."""

    id: str
    user_id: str
    title: str
    document_ids: list[str]
    documents: list[ComparisonDocumentRef]
    findings: list[ComparisonFinding]
    summary: ComparisonSummary
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "document_ids": list(self.document_ids),
            "documents": [d.to_dict() for d in self.documents],
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentComparison:
        created_raw = data.get("created_at")
        if isinstance(created_raw, str):
            try:
                created_at = datetime.fromisoformat(created_raw)
            except Exception:
                created_at = datetime.now(UTC)
        elif isinstance(created_raw, datetime):
            created_at = created_raw
        else:
            created_at = datetime.now(UTC)

        updated_raw = data.get("updated_at")
        if isinstance(updated_raw, str):
            try:
                updated_at = datetime.fromisoformat(updated_raw)
            except Exception:
                updated_at = datetime.now(UTC)
        elif isinstance(updated_raw, datetime):
            updated_at = updated_raw
        else:
            updated_at = datetime.now(UTC)

        findings = [
            ComparisonFinding.from_dict(f_data) for f_data in data.get("findings", [])
        ]
        summary_data = data.get("summary")
        summary = (
            ComparisonSummary.from_dict(summary_data)
            if summary_data
            else ComparisonSummary.compute(findings)
        )

        return cls(
            id=str(data["id"]),
            user_id=str(data["user_id"]),
            title=str(data.get("title", "Document Comparison")),
            document_ids=[str(doc_id) for doc_id in data.get("document_ids", [])],
            documents=[
                ComparisonDocumentRef.from_dict(doc_data)
                for doc_data in data.get("documents", [])
            ],
            findings=findings,
            summary=summary,
            created_at=created_at,
            updated_at=updated_at,
        )
