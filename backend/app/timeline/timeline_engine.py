"""Deterministic Timeline Synthesis Engine (Phase 14).

Extracts and orders timeline milestones from Phase 6 dates and obligations,
strictly separating explicit document facts from derived calculations, and
handling missing trigger dates safely without legal speculation.
"""

import re
import uuid
from datetime import datetime, timedelta

from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedDate,
    ExtractedObligation,
)
from app.timeline.models import (
    TimelineDateType,
    TimelineEvidenceRef,
    TimelineItem,
    TimelineItemStatus,
)
from app.trust.models import SafetyStatus, TrustTier


class TimelineEngine:
    """Deterministic timeline generation and relative deadline resolution engine."""

    @classmethod
    def build_timeline(
        cls,
        document_id: str,
        document_title: str,
        understanding: DocumentUnderstanding,
    ) -> list[TimelineItem]:
        """Synthesize chronological timeline items from extracted dates and
        obligations.
        """
        items: list[TimelineItem] = []

        # Index explicit dates by normalized date and date type
        explicit_dates_by_type: dict[str, ExtractedDate] = {}
        for d in understanding.dates:
            if d.date_type:
                explicit_dates_by_type[d.date_type.strip().lower()] = d
            if d.description:
                explicit_dates_by_type[d.description.strip().lower()] = d

            # Add explicit date item
            date_type = (
                TimelineDateType.FIXED_DATE
                if d.normalized_date
                else TimelineDateType.RELATIVE_DEADLINE
            )
            items.append(
                TimelineItem(
                    id=str(uuid.uuid4()),
                    title=f"Date: {d.description or d.date_type or 'Specified Date'}",
                    date_type=date_type,
                    item_status=TimelineItemStatus.EXPLICIT_FACT,
                    raw_date_text=d.raw_text,
                    calendar_date=d.normalized_date,
                    derived_date=None,
                    party="",
                    duty_or_event=d.description or "Document milestone",
                    section=f"Page {d.page_number}",
                    evidence_references=[
                        TimelineEvidenceRef(
                            document_id=document_id,
                            document_title=document_title,
                            page_start=d.page_number,
                            page_end=d.page_number,
                            source_span=d.source_span,
                            exact_quote=(
                                f"Date: {d.raw_text} ({d.description or d.date_type})"
                            ).strip(),
                            section="Dates",
                        )
                    ],
                    trust_tier=TrustTier.DOCUMENT_FACT,
                    safety_status=SafetyStatus.SAFE,
                    notes=f"Explicit date stated in document: '{d.raw_text}'.",
                )
            )

        # Process obligations
        for ob in understanding.obligations:
            deadline_str = (ob.deadline or "").strip()
            duty_str = (ob.duty or "").strip()

            if not deadline_str:
                # Undated obligation
                items.append(
                    TimelineItem(
                        id=str(uuid.uuid4()),
                        title=f"Obligation: {ob.obligor}",
                        date_type=TimelineDateType.UNSPECIFIED,
                        item_status=TimelineItemStatus.EXPLICIT_FACT,
                        raw_date_text="Unspecified deadline",
                        calendar_date=None,
                        derived_date=None,
                        party=ob.obligor,
                        duty_or_event=duty_str,
                        section=f"Pages {ob.page_start}-{ob.page_end}",
                        evidence_references=[
                            TimelineEvidenceRef(
                                document_id=document_id,
                                document_title=document_title,
                                page_start=ob.page_start,
                                page_end=ob.page_end,
                                source_span=ob.source_span,
                                exact_quote=f"Obligor: {ob.obligor} | Duty: {ob.duty}",
                                section="Obligations",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                        notes="Obligation stated without specific date anchor.",
                    )
                )
                continue

            # Check if deadline is a relative offset with anchor date
            days_match = re.search(r"(\d+)\s*days?", deadline_str, re.IGNORECASE)
            anchor_date = cls._find_anchor_date(
                ob, explicit_dates_by_type, understanding.dates
            )

            if days_match and anchor_date and anchor_date.normalized_date:
                # Mechanically derive target date
                try:
                    offset_days = int(days_match.group(1))
                    base_dt = datetime.strptime(
                        anchor_date.normalized_date, "%Y-%m-%d"
                    ).date()
                    target_dt = base_dt + timedelta(days=offset_days)
                    derived_iso = target_dt.strftime("%Y-%m-%d")

                    items.append(
                        TimelineItem(
                            id=str(uuid.uuid4()),
                            title=f"Relative Deadline: {ob.obligor}",
                            date_type=TimelineDateType.RELATIVE_DEADLINE,
                            item_status=TimelineItemStatus.DERIVED,
                            raw_date_text=deadline_str,
                            calendar_date=derived_iso,
                            derived_date=derived_iso,
                            inputs_used=[
                                f"Trigger Date: {anchor_date.raw_text} "
                                f"({anchor_date.normalized_date})",
                                f"Offset: {offset_days} calendar days",
                            ],
                            party=ob.obligor,
                            duty_or_event=duty_str,
                            section=f"Pages {ob.page_start}-{ob.page_end}",
                            evidence_references=[
                                TimelineEvidenceRef(
                                    document_id=document_id,
                                    document_title=document_title,
                                    page_start=ob.page_start,
                                    page_end=ob.page_end,
                                    source_span=ob.source_span,
                                    exact_quote=(
                                        f"Obligor: {ob.obligor} | Duty: {ob.duty} "
                                        f"| Deadline: {ob.deadline}"
                                    ),
                                    section="Obligations",
                                )
                            ],
                            trust_tier=TrustTier.DOCUMENT_FACT,
                            safety_status=SafetyStatus.SAFE,
                            notes=(
                                f"Derived date calculated from explicit base "
                                f"date '{anchor_date.normalized_date}' and "
                                f"{offset_days}-day period. (Calendar day "
                                f"calculation; local business-day rules not "
                                f"applied)."
                            ),
                        )
                    )
                    continue
                except Exception:
                    pass

            # Check for pure duration without relative trigger
            if not ob.trigger and re.match(
                r"^\d+\s+(year|month|week|day)s?$", deadline_str, re.IGNORECASE
            ):
                items.append(
                    TimelineItem(
                        id=str(uuid.uuid4()),
                        title=f"Duration: {ob.obligor}",
                        date_type=TimelineDateType.DURATION,
                        item_status=TimelineItemStatus.EXPLICIT_FACT,
                        raw_date_text=deadline_str,
                        calendar_date=None,
                        derived_date=None,
                        party=ob.obligor,
                        duty_or_event=duty_str,
                        section=f"Pages {ob.page_start}-{ob.page_end}",
                        evidence_references=[
                            TimelineEvidenceRef(
                                document_id=document_id,
                                document_title=document_title,
                                page_start=ob.page_start,
                                page_end=ob.page_end,
                                source_span=ob.source_span,
                                exact_quote=(
                                    f"Obligor: {ob.obligor} | Duty: {ob.duty} "
                                    f"| Duration: {ob.deadline}"
                                ),
                                section="Obligations",
                            )
                        ],
                        trust_tier=TrustTier.DOCUMENT_FACT,
                        safety_status=SafetyStatus.SAFE,
                        notes=f"Duration of {deadline_str} specified in document.",
                    )
                )
                continue

            # Missing anchor date or non-derivable relative trigger
            cls._add_unresolved_timeline_item(
                items, document_id, document_title, ob, deadline_str, duty_str
            )

        # Sort timeline: dated items chronologically, followed by undated
        def sort_key(item: TimelineItem) -> tuple[int, str]:
            date_val = item.calendar_date or item.derived_date
            if date_val:
                return (0, date_val)
            return (1, item.title)

        items.sort(key=sort_key)
        return items

    @staticmethod
    def _find_anchor_date(
        ob: ExtractedObligation,
        dates_by_type: dict[str, ExtractedDate],
        all_dates: list[ExtractedDate],
    ) -> ExtractedDate | None:
        """Find matching anchor date for an obligation trigger if explicitly
        available.
        """
        trigger = (ob.trigger or "").lower().strip()
        deadline = (ob.deadline or "").lower().strip()

        # Check trigger keywords
        for key, dt in dates_by_type.items():
            if key in trigger or trigger in key or key in deadline or deadline in key:
                if dt.normalized_date:
                    return dt

        # If trigger mentions invoice, commencement, effective, execution
        for dt in all_dates:
            desc = (dt.description or dt.date_type or "").lower()
            if (
                ("effective" in desc and "effective" in trigger)
                or ("commence" in desc and "commence" in trigger)
                or ("invoice" in desc and "invoice" in trigger)
            ):
                if dt.normalized_date:
                    return dt

        # If single effective date exists and trigger is start/effective
        if len(all_dates) == 1 and all_dates[0].normalized_date:
            if "effective" in trigger or "commencement" in trigger:
                return all_dates[0]

        return None

    @staticmethod
    def _add_unresolved_timeline_item(
        items: list[TimelineItem],
        document_id: str,
        document_title: str,
        ob: ExtractedObligation,
        deadline_str: str,
        duty_str: str,
    ) -> None:
        """Record relative deadline with missing trigger as UNRESOLVED_TRIGGER."""
        items.append(
            TimelineItem(
                id=str(uuid.uuid4()),
                title=f"Relative Deadline (Missing Trigger): {ob.obligor}",
                date_type=TimelineDateType.RELATIVE_DEADLINE,
                item_status=TimelineItemStatus.UNRESOLVED_TRIGGER,
                raw_date_text=deadline_str,
                calendar_date=None,
                derived_date=None,
                inputs_used=[],
                party=ob.obligor,
                duty_or_event=duty_str,
                section=f"Pages {ob.page_start}-{ob.page_end}",
                evidence_references=[
                    TimelineEvidenceRef(
                        document_id=document_id,
                        document_title=document_title,
                        page_start=ob.page_start,
                        page_end=ob.page_end,
                        source_span=ob.source_span,
                        exact_quote=(
                            f"Obligor: {ob.obligor} | Duty: {ob.duty} "
                            f"| Deadline: {ob.deadline}"
                        ),
                        section="Obligations",
                    )
                ],
                trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
                safety_status=SafetyStatus.REVIEW_REQUIRED,
                notes=(
                    f"The relative deadline '{deadline_str}' requires an "
                    "external or unspecified trigger date that was not "
                    "identified in the document."
                ),
            )
        )
