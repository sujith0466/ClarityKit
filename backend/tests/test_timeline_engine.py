"""Unit tests for TimelineEngine synthesis and derived date logic (Phase 14)."""

import uuid

from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedDate,
    ExtractedObligation,
)
from app.timeline.models import (
    TimelineDateType,
    TimelineItemStatus,
)
from app.timeline.timeline_engine import TimelineEngine
from app.trust.models import SafetyStatus, TrustTier


def test_timeline_engine_fixed_dates_and_durations() -> None:
    doc_id = str(uuid.uuid4())
    understanding = DocumentUnderstanding(
        document_id=doc_id,
        parties=[],
        dates=[
            ExtractedDate.create(
                document_id=doc_id,
                raw_text="January 15, 2026",
                normalized_date="2026-01-15",
                date_type="effective_date",
                description="Effective Date",
                page_number=1,
                source_span="January 15, 2026",
            ),
            ExtractedDate.create(
                document_id=doc_id,
                raw_text="December 31, 2026",
                normalized_date="2026-12-31",
                date_type="expiration_date",
                description="Expiration",
                page_number=4,
                source_span="December 31, 2026",
            ),
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc_id,
                obligor="Tenant",
                duty="Lease term",
                trigger=None,
                deadline="12 months",
                page_start=1,
                page_end=1,
                source_span="term of 12 months",
            )
        ],
        clauses=[],
        review_flags=[],
    )

    items = TimelineEngine.build_timeline(
        document_id=doc_id,
        document_title="Lease.pdf",
        understanding=understanding,
    )

    assert len(items) == 3

    # Check fixed dates
    fixed_items = [i for i in items if i.date_type == TimelineDateType.FIXED_DATE]
    assert len(fixed_items) == 2
    assert fixed_items[0].calendar_date == "2026-01-15"
    assert fixed_items[1].calendar_date == "2026-12-31"

    # Check duration
    duration_item = next(i for i in items if i.date_type == TimelineDateType.DURATION)
    assert duration_item.raw_date_text == "12 months"
    assert duration_item.item_status == TimelineItemStatus.EXPLICIT_FACT


def test_timeline_engine_derived_date_with_explicit_trigger() -> None:
    doc_id = str(uuid.uuid4())
    understanding = DocumentUnderstanding(
        document_id=doc_id,
        parties=[],
        dates=[
            ExtractedDate.create(
                document_id=doc_id,
                date_type="milestone_date",
                raw_text="March 1, 2026",
                normalized_date="2026-03-01",
                description="Invoice Date",
                page_number=1,
                source_span="March 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc_id,
                obligor="Client",
                duty="Pay consulting fees",
                trigger="Invoice Date",
                deadline="30 days",
                page_start=2,
                page_end=2,
                source_span="within 30 days after invoice date",
            )
        ],
        clauses=[],
        review_flags=[],
    )

    items = TimelineEngine.build_timeline(
        document_id=doc_id,
        document_title="Services_Agreement.pdf",
        understanding=understanding,
    )

    assert len(items) == 2

    derived_item = next(i for i in items if i.item_status == TimelineItemStatus.DERIVED)
    assert derived_item.derived_date == "2026-03-31"
    assert derived_item.date_type == TimelineDateType.RELATIVE_DEADLINE
    assert len(derived_item.inputs_used) == 2
    assert "Trigger Date: March 1, 2026 (2026-03-01)" in derived_item.inputs_used[0]


def test_timeline_engine_missing_trigger_safety_fallback() -> None:
    doc_id = str(uuid.uuid4())
    understanding = DocumentUnderstanding(
        document_id=doc_id,
        parties=[],
        dates=[],  # No anchor dates extracted
        obligations=[
            ExtractedObligation.create(
                document_id=doc_id,
                obligor="Tenant",
                duty="Deliver notice of renewal",
                trigger="expiration of lease",
                deadline="60 days prior to expiration",
                page_start=3,
                page_end=3,
                source_span="60 days prior to expiration",
            )
        ],
        clauses=[],
        review_flags=[],
    )

    items = TimelineEngine.build_timeline(
        document_id=doc_id,
        document_title="Lease.pdf",
        understanding=understanding,
    )

    assert len(items) == 1
    unresolved_item = items[0]
    assert unresolved_item.item_status == TimelineItemStatus.UNRESOLVED_TRIGGER
    assert unresolved_item.calendar_date is None
    assert unresolved_item.derived_date is None
    assert unresolved_item.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert unresolved_item.safety_status == SafetyStatus.REVIEW_REQUIRED
