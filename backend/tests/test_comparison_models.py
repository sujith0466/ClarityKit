"""Unit tests for Comparison domain models, enums, and schemas (Phase 13)."""

import uuid
from datetime import UTC, datetime

from app.comparison.models import (
    ComparisonCategory,
    ComparisonDocumentRef,
    ComparisonFinding,
    ComparisonSummary,
    DifferenceClassification,
    DocumentComparison,
    DocumentEvidenceRef,
)
from app.evidence.models import EvidenceValidationStatus
from app.trust.models import SafetyStatus, TrustTier


def test_comparison_category_enums() -> None:
    """Verify all 10 standard comparison categories are defined."""
    expected = {
        "PARTIES",
        "DATES",
        "OBLIGATIONS",
        "TERMINATION",
        "PAYMENT",
        "DURATION",
        "CLAUSE",
        "DEFINITIONS",
        "NOTICE",
        "OTHER",
    }
    actual = {cat.value for cat in ComparisonCategory}
    assert actual == expected


def test_difference_classification_enums() -> None:
    """Verify all 5 domain comparison classifications are defined."""
    expected = {
        "MATCH",
        "DIFFERENT",
        "PRESENT_IN_ONE_ONLY",
        "POTENTIAL_INCONSISTENCY",
        "UNRESOLVED",
    }
    actual = {diff.value for diff in DifferenceClassification}
    assert actual == expected


def test_document_evidence_ref_serialization() -> None:
    """Verify DocumentEvidenceRef to_dict and from_dict roundtrip."""
    doc_id = str(uuid.uuid4())
    ref = DocumentEvidenceRef(
        document_id=doc_id,
        document_title="Employment Agreement.pdf",
        page_start=1,
        page_end=2,
        source_span="Employee shall receive $120,000 annually.",
        section="Compensation",
        exact_quote="Employee shall receive $120,000 annually.",
        char_start=10,
        char_end=51,
        validation_status=EvidenceValidationStatus.VALID,
        trust_tier=TrustTier.DOCUMENT_FACT,
    )

    data = ref.to_dict()
    assert data["document_id"] == doc_id
    assert data["validation_status"] == "VALID"
    assert data["trust_tier"] == "DOCUMENT_FACT"

    restored = DocumentEvidenceRef.from_dict(data)
    assert restored.document_id == ref.document_id
    assert restored.validation_status == EvidenceValidationStatus.VALID
    assert restored.trust_tier == TrustTier.DOCUMENT_FACT


def test_comparison_finding_serialization() -> None:
    """Verify ComparisonFinding to_dict and from_dict roundtrip."""
    finding_id = str(uuid.uuid4())
    finding = ComparisonFinding(
        id=finding_id,
        category=ComparisonCategory.DATES,
        title="Differing Start Dates",
        description="Offer letter specifies Oct 1 while Contract specifies Oct 15.",
        classification=DifferenceClassification.POTENTIAL_INCONSISTENCY,
        evidence_references=[],
        lawyer_questions=["Which start date governs the commencement of employment?"],
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.REVIEW_REQUIRED,
    )

    data = finding.to_dict()
    assert data["id"] == finding_id
    assert data["category"] == "DATES"
    assert data["classification"] == "POTENTIAL_INCONSISTENCY"
    assert len(data["lawyer_questions"]) == 1

    restored = ComparisonFinding.from_dict(data)
    assert restored.id == finding.id
    assert restored.category == ComparisonCategory.DATES
    assert restored.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
    assert restored.safety_status == SafetyStatus.REVIEW_REQUIRED


def test_comparison_summary_computation() -> None:
    """Verify summary metrics aggregation over findings."""
    f1 = ComparisonFinding(
        id="1",
        category=ComparisonCategory.PARTIES,
        title="Parties",
        description="Matches",
        classification=DifferenceClassification.MATCH,
    )
    f2 = ComparisonFinding(
        id="2",
        category=ComparisonCategory.DATES,
        title="Dates",
        description="Differs",
        classification=DifferenceClassification.POTENTIAL_INCONSISTENCY,
    )
    f3 = ComparisonFinding(
        id="3",
        category=ComparisonCategory.CLAUSE,
        title="Missing in one",
        description="Missing",
        classification=DifferenceClassification.PRESENT_IN_ONE_ONLY,
    )

    summary = ComparisonSummary.compute([f1, f2, f3])
    assert summary.total_findings == 3
    assert summary.match_count == 1
    assert summary.potential_inconsistency_count == 1
    assert summary.present_in_one_only_count == 1
    assert summary.difference_count == 0
    assert summary.unresolved_count == 0


def test_document_comparison_serialization() -> None:
    """Verify full DocumentComparison serialization."""
    comp_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    docs = [
        ComparisonDocumentRef(
            document_id=doc1_id,
            title="Doc A",
            filename="doc_a.pdf",
            page_count=2,
        ),
        ComparisonDocumentRef(
            document_id=doc2_id,
            title="Doc B",
            filename="doc_b.pdf",
            page_count=3,
        ),
    ]

    finding = ComparisonFinding(
        id="f1",
        category=ComparisonCategory.TERMINATION,
        title="Notice Period",
        description="30 vs 60 days",
        classification=DifferenceClassification.POTENTIAL_INCONSISTENCY,
    )

    comp = DocumentComparison(
        id=comp_id,
        user_id=user_id,
        title="Offer Letter vs Employment Agreement",
        document_ids=[doc1_id, doc2_id],
        documents=docs,
        findings=[finding],
        summary=ComparisonSummary.compute([finding]),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    data = comp.to_dict()
    assert data["id"] == comp_id
    assert data["user_id"] == user_id
    assert len(data["documents"]) == 2
    assert len(data["findings"]) == 1

    restored = DocumentComparison.from_dict(data)
    assert restored.id == comp_id
    assert restored.user_id == user_id
    assert len(restored.documents) == 2
    assert restored.summary.potential_inconsistency_count == 1
