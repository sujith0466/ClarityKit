"""Unit tests for Lawyer Preparation Brief domain models."""

from app.brief.models import (
    BriefItem,
    BriefQuestion,
    BriefSection,
    BriefSourceType,
    LawyerPreparationBrief,
)
from app.evidence.models import EvidenceReference
from app.trust.models import SafetyStatus, TrustTier


def test_brief_item_serialization() -> None:
    ev = EvidenceReference(
        document_id="doc-1", page_start=1, page_end=1, source_span="Payment is $1000"
    )

    item = BriefItem(
        id="item-1",
        text="Payment is $1000",
        title="Payment Duty",
        content="Tenant must pay $1000",
        source_type=BriefSourceType.OBLIGATION,
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
        page_start=1,
        page_end=1,
        source_span="Payment is $1000",
        evidence=ev,
    )
    d = item.to_dict()
    assert d["id"] == "item-1"
    assert d["source_type"] == "OBLIGATION"
    assert d["trust_tier"] == "DOCUMENT_FACT"
    assert d["evidence"]["source_span"] == "Payment is $1000"

    restored = BriefItem.from_dict(d)
    assert restored.id == item.id
    assert restored.source_type == item.source_type
    assert restored.evidence is not None
    assert restored.evidence.source_span == "Payment is $1000"


def test_brief_section_serialization() -> None:
    item = BriefItem(
        id="it-1",
        text="Party Acme Corp",
        source_type=BriefSourceType.PARTY,
        trust_tier=TrustTier.DOCUMENT_FACT,
    )
    section = BriefSection(
        section_key="parties",
        title="Parties",
        description="Identified participants",
        items=[item],
    )
    d = section.to_dict()
    assert d["section_key"] == "parties"
    assert len(d["items"]) == 1

    restored = BriefSection.from_dict(d)
    assert restored.section_key == "parties"
    assert len(restored.items) == 1
    assert restored.items[0].id == "it-1"


def test_lawyer_brief_serialization() -> None:
    brief = LawyerPreparationBrief(
        id="brief-1",
        document_id="doc-1",
        title="Lawyer Preparation Brief — Lease.pdf",
        situation_summary="Summary of lease agreement.",
        sections={},
        questions_for_lawyer=[
            BriefQuestion(
                question="What is the standard for termination notice?",
                category="termination",
                rationale="Clause 5 specifies 30 days.",
            )
        ],
        facts_to_confirm=["Confirm landlord legal entity name"],
        documents_to_bring=["Signed lease agreement"],
        open_questions=["Is there a renewal addendum?"],
        completeness_score=0.8,
    )
    d = brief.to_dict()
    assert d["id"] == "brief-1"
    assert d["document_id"] == "doc-1"
    assert len(d["questions_for_lawyer"]) == 1
    assert d["completeness_score"] == 0.8
    assert "IMPORTANT NOTICE" in d["disclaimer"]

    restored = LawyerPreparationBrief.from_dict(d)
    assert restored.id == "brief-1"
    assert restored.document_id == "doc-1"
    assert len(restored.questions_for_lawyer) == 1
    assert (
        restored.questions_for_lawyer[0].question
        == "What is the standard for termination notice?"
    )
