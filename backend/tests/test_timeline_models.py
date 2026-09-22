"""Unit tests for Timeline domain models and serialization (Phase 14)."""

import uuid

from app.evidence.models import EvidenceValidationStatus
from app.timeline.models import (
    DocumentTimeline,
    TimelineDateType,
    TimelineEvidenceRef,
    TimelineItem,
    TimelineItemStatus,
    TimelineSummary,
)
from app.trust.models import SafetyStatus, TrustTier


def test_timeline_evidence_ref_serialization() -> None:
    doc_id = str(uuid.uuid4())
    ref = TimelineEvidenceRef(
        document_id=doc_id,
        document_title="Master_Agreement.pdf",
        page_start=2,
        page_end=2,
        source_span="Effective as of January 1, 2026",
        exact_quote="Effective as of January 1, 2026",
        section="Section 1",
        validation_status=EvidenceValidationStatus.VALID,
        char_start=50,
        char_end=81,
    )

    data = ref.to_dict()
    assert data["document_id"] == doc_id
    assert data["validation_status"] == "VALID"
    assert data["char_start"] == 50

    deserialized = TimelineEvidenceRef.from_dict(data)
    assert deserialized.document_id == doc_id
    assert deserialized.validation_status == EvidenceValidationStatus.VALID


def test_timeline_item_serialization() -> None:
    item_id = str(uuid.uuid4())
    item = TimelineItem(
        id=item_id,
        title="Payment Milestone",
        date_type=TimelineDateType.RELATIVE_DEADLINE,
        item_status=TimelineItemStatus.DERIVED,
        raw_date_text="within 30 days after invoice",
        calendar_date="2026-03-31",
        derived_date="2026-03-31",
        inputs_used=["Invoice Date: 2026-03-01", "Offset: 30 days"],
        party="Client",
        duty_or_event="Pay invoice amount",
        section="Payment",
        evidence_references=[],
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
        notes="Derived from March 1, 2026 invoice date.",
    )

    data = item.to_dict()
    assert data["id"] == item_id
    assert data["item_status"] == "DERIVED"
    assert data["derived_date"] == "2026-03-31"
    assert len(data["inputs_used"]) == 2

    deserialized = TimelineItem.from_dict(data)
    assert deserialized.id == item_id
    assert deserialized.item_status == TimelineItemStatus.DERIVED
    assert deserialized.derived_date == "2026-03-31"


def test_document_timeline_full_roundtrip() -> None:
    tl_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    item = TimelineItem(
        id=str(uuid.uuid4()),
        title="Effective Date",
        date_type=TimelineDateType.FIXED_DATE,
        item_status=TimelineItemStatus.EXPLICIT_FACT,
        raw_date_text="January 15, 2026",
        calendar_date="2026-01-15",
    )

    summary = TimelineSummary.from_items([item])
    assert summary.total_items == 1
    assert summary.fixed_date_count == 1

    timeline = DocumentTimeline(
        id=tl_id,
        user_id=user_id,
        document_id=doc_id,
        document_title="Contract.pdf",
        items=[item],
        summary=summary,
    )

    data = timeline.to_dict()
    deserialized = DocumentTimeline.from_dict(data)

    assert deserialized.id == tl_id
    assert deserialized.document_id == doc_id
    assert len(deserialized.items) == 1
    assert deserialized.summary.fixed_date_count == 1
