from dataclasses import dataclass, field
from typing import Any


class ReasoningError(Exception):
    """Base exception for reasoning provider operations."""

    pass


@dataclass
class ReasoningRequest:
    """Input payload for a reasoning/extraction request."""

    document_id: str
    pages: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawExtractedParty:
    name: str
    role: str
    page_number: int
    source_span: str


@dataclass
class RawExtractedClause:
    clause_identifier: str
    title: str
    category: str
    text: str
    page_start: int
    page_end: int
    source_span: str


@dataclass
class RawExtractedObligation:
    obligor: str
    duty: str
    trigger: str | None
    deadline: str | None
    page_start: int
    page_end: int
    source_span: str
    related_clause_identifier: str | None = None


@dataclass
class RawExtractedDate:
    date_type: str
    raw_text: str
    normalized_date: str | None
    description: str
    page_number: int
    source_span: str


@dataclass
class RawExtractedReviewFlag:
    flag_type: str
    title: str
    description: str
    severity: str
    page_start: int
    page_end: int
    source_span: str
    related_clause_identifier: str | None = None


@dataclass
class RawExtractionResult:
    """Structured extraction output produced by a reasoning provider."""

    parties: list[RawExtractedParty] = field(default_factory=list)
    clauses: list[RawExtractedClause] = field(default_factory=list)
    obligations: list[RawExtractedObligation] = field(default_factory=list)
    dates: list[RawExtractedDate] = field(default_factory=list)
    review_flags: list[RawExtractedReviewFlag] = field(default_factory=list)
    provider_info: dict[str, Any] = field(default_factory=dict)
