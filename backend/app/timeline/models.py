"""Domain models and data structures for Deadline & Obligation Timeline (Phase 14)."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.evidence.models import EvidenceValidationStatus
from app.trust.models import SafetyStatus, TrustTier


class TimelineError(Exception):
    """Base exception for timeline operations."""


class TimelineNotFoundError(TimelineError):
    """Raised when a timeline or document is not found or unauthorized (404)."""


class InvalidTimelineInputError(TimelineError):
    """Raised when timeline input parameters violate constraints."""


class DocumentNotReadyForTimelineError(TimelineError):
    """Raised when a document is not in 'ready' status for timeline generation."""


class TimelineDateType(str, Enum):
    """Classification of date types represented in the timeline."""

    FIXED_DATE = "FIXED_DATE"
    RELATIVE_DEADLINE = "RELATIVE_DEADLINE"
    DURATION = "DURATION"
    RECURRING = "RECURRING"
    UNSPECIFIED = "UNSPECIFIED"


class TimelineItemStatus(str, Enum):
    """Distinction between explicit document facts and derived calculations."""

    EXPLICIT_FACT = "EXPLICIT_FACT"
    DERIVED = "DERIVED"
    UNRESOLVED_TRIGGER = "UNRESOLVED_TRIGGER"


@dataclass
class TimelineEvidenceRef:
    """Evidence citation associated with a timeline event or obligation."""

    document_id: str
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
    def from_dict(cls, data: dict[str, Any]) -> "TimelineEvidenceRef":
        return cls(
            document_id=data["document_id"],
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
class TimelineItem:
    """Individual chronological milestone, obligation, or deadline."""

    id: str
    title: str
    date_type: TimelineDateType
    item_status: TimelineItemStatus
    raw_date_text: str
    calendar_date: str | None = None  # "YYYY-MM-DD" if fixed or derived
    derived_date: str | None = None
    inputs_used: list[str] = field(default_factory=list)
    party: str = ""
    duty_or_event: str = ""
    section: str = ""
    evidence_references: list[TimelineEvidenceRef] = field(default_factory=list)
    trust_tier: TrustTier = TrustTier.DOCUMENT_FACT
    safety_status: SafetyStatus = SafetyStatus.SAFE
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "date_type": self.date_type.value,
            "item_status": self.item_status.value,
            "raw_date_text": self.raw_date_text,
            "calendar_date": self.calendar_date,
            "derived_date": self.derived_date,
            "inputs_used": list(self.inputs_used),
            "party": self.party,
            "duty_or_event": self.duty_or_event,
            "section": self.section,
            "evidence_references": [e.to_dict() for e in self.evidence_references],
            "trust_tier": self.trust_tier.value,
            "safety_status": self.safety_status.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimelineItem":
        return cls(
            id=data["id"],
            title=data["title"],
            date_type=TimelineDateType(data["date_type"]),
            item_status=TimelineItemStatus(data["item_status"]),
            raw_date_text=data.get("raw_date_text", ""),
            calendar_date=data.get("calendar_date"),
            derived_date=data.get("derived_date"),
            inputs_used=list(data.get("inputs_used", [])),
            party=data.get("party", ""),
            duty_or_event=data.get("duty_or_event", ""),
            section=data.get("section", ""),
            evidence_references=[
                TimelineEvidenceRef.from_dict(e)
                for e in data.get("evidence_references", [])
            ],
            trust_tier=TrustTier(data.get("trust_tier", TrustTier.DOCUMENT_FACT.value)),
            safety_status=SafetyStatus(
                data.get("safety_status", SafetyStatus.SAFE.value)
            ),
            notes=data.get("notes", ""),
        )


@dataclass
class TimelineSummary:
    """Summary metrics of dates and obligations across the document."""

    total_items: int = 0
    fixed_date_count: int = 0
    derived_count: int = 0
    relative_deadline_count: int = 0
    unresolved_trigger_count: int = 0
    duration_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimelineSummary":
        return cls(
            total_items=int(data.get("total_items", 0)),
            fixed_date_count=int(data.get("fixed_date_count", 0)),
            derived_count=int(data.get("derived_count", 0)),
            relative_deadline_count=int(data.get("relative_deadline_count", 0)),
            unresolved_trigger_count=int(data.get("unresolved_trigger_count", 0)),
            duration_count=int(data.get("duration_count", 0)),
        )

    @classmethod
    def from_items(cls, items: list[TimelineItem]) -> "TimelineSummary":
        return cls(
            total_items=len(items),
            fixed_date_count=sum(
                1 for i in items if i.date_type == TimelineDateType.FIXED_DATE
            ),
            derived_count=sum(
                1 for i in items if i.item_status == TimelineItemStatus.DERIVED
            ),
            relative_deadline_count=sum(
                1 for i in items if i.date_type == TimelineDateType.RELATIVE_DEADLINE
            ),
            unresolved_trigger_count=sum(
                1
                for i in items
                if i.item_status == TimelineItemStatus.UNRESOLVED_TRIGGER
            ),
            duration_count=sum(
                1 for i in items if i.date_type == TimelineDateType.DURATION
            ),
        )


@dataclass
class DocumentTimeline:
    """Chronological timeline aggregate for a document."""

    id: str
    user_id: str
    document_id: str
    document_title: str
    title: str = "Document Timeline"
    items: list[TimelineItem] = field(default_factory=list)
    summary: TimelineSummary = field(default_factory=TimelineSummary)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "title": self.title,
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentTimeline":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            document_id=data["document_id"],
            document_title=data.get("document_title", ""),
            title=data.get("title", "Document Timeline"),
            items=[TimelineItem.from_dict(i) for i in data.get("items", [])],
            summary=TimelineSummary.from_dict(data.get("summary", {})),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )
