import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ExtractionError(Exception):
    """Base exception for structured extraction operations."""

    pass


class DocumentNotFoundError(ExtractionError):
    """Raised when the target document does not exist or is not accessible."""

    pass


class InvalidExtractionSchemaError(ExtractionError):
    """Raised when extracted data fails validation rules or structural checks."""

    pass


class DocumentNotReadyForExtractionError(ExtractionError):
    """Raised when extraction is attempted on a document not in READY status."""

    pass


class ProvenanceValidationError(ExtractionError):
    """Raised when provenance source span does not match underlying page text."""

    pass


class ClauseCategory(str, Enum):
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    PAYMENT = "payment"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    NON_COMPETE = "non_compete"
    NON_SOLICIT = "non_solicit"
    DISPUTE_RESOLUTION = "dispute_resolution"
    NOTICES = "notices"
    SEVERABILITY = "severability"
    REPRESENTATIONS = "representations"
    GENERAL = "general"


class DateType(str, Enum):
    EFFECTIVE_DATE = "effective_date"
    EXPIRATION_DATE = "expiration_date"
    RENEWAL_DEADLINE = "renewal_deadline"
    PAYMENT_DUE_DATE = "payment_due_date"
    NOTICE_DEADLINE = "notice_deadline"
    MILESTONE_DATE = "milestone_date"
    EXECUTION_DATE = "execution_date"


class ReviewFlagType(str, Enum):
    RESTRICTIVE_COVENANT = "restrictive_covenant"
    RENEWAL_LOCK_IN = "renewal_lock_in"
    UNILATERAL_DISCRETION = "unilateral_discretion"
    AMBIGUOUS_TERM = "ambiguous_term"
    MISSING_STANDARD_TERM = "missing_standard_term"
    GENERAL_NOTICE = "general_notice"


@dataclass
class ExtractedParty:
    """Legal party or entity identified in document."""

    id: str
    document_id: str
    name: str
    role: str
    page_number: int
    source_span: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        name: str,
        role: str,
        page_number: int,
        source_span: str,
        party_id: str | None = None,
    ) -> "ExtractedParty":
        clean_name = name.strip()
        clean_role = role.strip()
        if not clean_name:
            raise InvalidExtractionSchemaError("Party name cannot be empty.")
        if not clean_role:
            clean_role = "Party"
        if page_number < 1:
            raise InvalidExtractionSchemaError("Page number must be >= 1.")

        return cls(
            id=party_id or str(uuid.uuid4()),
            document_id=document_id,
            name=clean_name,
            role=clean_role,
            page_number=page_number,
            source_span=source_span.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "name": self.name,
            "role": self.role,
            "page_number": self.page_number,
            "source_span": self.source_span,
            "created_at": self.created_at,
        }


@dataclass
class ExtractedClause:
    """Identified section or clause within the document."""

    id: str
    document_id: str
    clause_identifier: str
    title: str
    category: str
    text: str
    page_start: int
    page_end: int
    source_span: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        clause_identifier: str,
        title: str,
        category: str,
        text: str,
        page_start: int,
        page_end: int,
        source_span: str,
        clause_id: str | None = None,
    ) -> "ExtractedClause":
        clean_ident = clause_identifier.strip()
        clean_title = title.strip()
        clean_text = text.strip()
        if not clean_title:
            raise InvalidExtractionSchemaError("Clause title cannot be empty.")
        if page_start < 1 or page_end < page_start:
            raise InvalidExtractionSchemaError("Invalid clause page range.")

        valid_cat = (
            category.lower()
            if category.lower() in [c.value for c in ClauseCategory]
            else ClauseCategory.GENERAL.value
        )

        return cls(
            id=clause_id or str(uuid.uuid4()),
            document_id=document_id,
            clause_identifier=clean_ident or "Clause",
            title=clean_title,
            category=valid_cat,
            text=clean_text,
            page_start=page_start,
            page_end=page_end,
            source_span=source_span.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "clause_identifier": self.clause_identifier,
            "title": self.title,
            "category": self.category,
            "text": self.text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "created_at": self.created_at,
        }


@dataclass
class ExtractedObligation:
    """Specific legal duty extracted with trigger, obligor, and deadline."""

    id: str
    document_id: str
    obligor: str
    duty: str
    trigger: str | None
    deadline: str | None
    page_start: int
    page_end: int
    source_span: str
    clause_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        obligor: str,
        duty: str,
        trigger: str | None,
        deadline: str | None,
        page_start: int,
        page_end: int,
        source_span: str,
        clause_id: str | None = None,
        obligation_id: str | None = None,
    ) -> "ExtractedObligation":
        clean_obligor = obligor.strip()
        clean_duty = duty.strip()
        if not clean_obligor:
            clean_obligor = "Party"
        if not clean_duty:
            raise InvalidExtractionSchemaError("Obligation duty cannot be empty.")
        if page_start < 1 or page_end < page_start:
            raise InvalidExtractionSchemaError("Invalid obligation page range.")

        return cls(
            id=obligation_id or str(uuid.uuid4()),
            document_id=document_id,
            clause_id=clause_id,
            obligor=clean_obligor,
            duty=clean_duty,
            trigger=trigger.strip() if trigger else None,
            deadline=deadline.strip() if deadline else None,
            page_start=page_start,
            page_end=page_end,
            source_span=source_span.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "clause_id": self.clause_id,
            "obligor": self.obligor,
            "duty": self.duty,
            "trigger": self.trigger,
            "deadline": self.deadline,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "created_at": self.created_at,
        }


@dataclass
class ExtractedDate:
    """Important contract or milestone date with optional ISO normalization."""

    id: str
    document_id: str
    date_type: str
    raw_text: str
    normalized_date: str | None
    description: str
    page_number: int
    source_span: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        date_type: str,
        raw_text: str,
        normalized_date: str | None,
        description: str,
        page_number: int,
        source_span: str,
        date_id: str | None = None,
    ) -> "ExtractedDate":
        clean_raw = raw_text.strip()
        clean_desc = description.strip()
        if not clean_raw:
            raise InvalidExtractionSchemaError("Raw date text cannot be empty.")
        if page_number < 1:
            raise InvalidExtractionSchemaError("Page number must be >= 1.")

        valid_type = (
            date_type.lower()
            if date_type.lower() in [d.value for d in DateType]
            else DateType.MILESTONE_DATE.value
        )

        return cls(
            id=date_id or str(uuid.uuid4()),
            document_id=document_id,
            date_type=valid_type,
            raw_text=clean_raw,
            normalized_date=normalized_date.strip() if normalized_date else None,
            description=clean_desc or "Date reference",
            page_number=page_number,
            source_span=source_span.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "date_type": self.date_type,
            "raw_text": self.raw_text,
            "normalized_date": self.normalized_date,
            "description": self.description,
            "page_number": self.page_number,
            "source_span": self.source_span,
            "created_at": self.created_at,
        }


@dataclass
class ExtractedReviewFlag:
    """Neutral advisory flag for terms that may warrant review (NO legal advice)."""

    id: str
    document_id: str
    flag_type: str
    title: str
    description: str
    severity: str
    page_start: int
    page_end: int
    source_span: str
    related_clause_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        document_id: str,
        flag_type: str,
        title: str,
        description: str,
        severity: str,
        page_start: int,
        page_end: int,
        source_span: str,
        related_clause_id: str | None = None,
        flag_id: str | None = None,
    ) -> "ExtractedReviewFlag":
        clean_title = title.strip()
        clean_desc = description.strip()
        clean_sev = severity.strip().lower()
        if not clean_title:
            raise InvalidExtractionSchemaError("Review flag title cannot be empty.")
        if not clean_desc:
            raise InvalidExtractionSchemaError(
                "Review flag description cannot be empty."
            )
        if clean_sev not in ("low", "medium", "high"):
            clean_sev = "medium"
        if page_start < 1 or page_end < page_start:
            raise InvalidExtractionSchemaError("Invalid review flag page range.")

        valid_type = (
            flag_type.lower()
            if flag_type.lower() in [f.value for f in ReviewFlagType]
            else ReviewFlagType.GENERAL_NOTICE.value
        )

        return cls(
            id=flag_id or str(uuid.uuid4()),
            document_id=document_id,
            related_clause_id=related_clause_id,
            flag_type=valid_type,
            title=clean_title,
            description=clean_desc,
            severity=clean_sev,
            page_start=page_start,
            page_end=page_end,
            source_span=source_span.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "related_clause_id": self.related_clause_id,
            "flag_type": self.flag_type,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_span": self.source_span,
            "created_at": self.created_at,
        }


@dataclass
class DocumentUnderstanding:
    """Aggregated structured understanding representation for a legal document."""

    document_id: str
    parties: list[ExtractedParty] = field(default_factory=list)
    clauses: list[ExtractedClause] = field(default_factory=list)
    obligations: list[ExtractedObligation] = field(default_factory=list)
    dates: list[ExtractedDate] = field(default_factory=list)
    review_flags: list[ExtractedReviewFlag] = field(default_factory=list)
    provider_info: dict[str, Any] = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "parties": [p.to_dict() for p in self.parties],
            "clauses": [c.to_dict() for c in self.clauses],
            "obligations": [o.to_dict() for o in self.obligations],
            "dates": [d.to_dict() for d in self.dates],
            "review_flags": [f.to_dict() for f in self.review_flags],
            "provider_info": self.provider_info,
            "extracted_at": self.extracted_at,
            "counts": {
                "parties": len(self.parties),
                "clauses": len(self.clauses),
                "obligations": len(self.obligations),
                "dates": len(self.dates),
                "review_flags": len(self.review_flags),
            },
        }
