"""Unit tests for deterministic ComparisonMatcher engine (Phase 13)."""

from app.comparison.matcher import ComparisonMatcher
from app.comparison.models import ComparisonCategory, DifferenceClassification
from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
)


def test_matcher_parties_matching_and_differing() -> None:
    """Test matching party roles vs differing party roles."""
    doc_a = "doc-a"
    doc_b = "doc-b"
    titles = {doc_a: "Offer Letter", doc_b: "Contract"}

    understanding_a = DocumentUnderstanding(
        document_id=doc_a,
        parties=[
            ExtractedParty.create(
                document_id=doc_a,
                name="Acme Corp",
                role="Employer",
                page_number=1,
                source_span="Acme Corp (Employer)",
            ),
            ExtractedParty.create(
                document_id=doc_a,
                name="John Doe",
                role="Engineer",
                page_number=1,
                source_span="John Doe (Engineer)",
            ),
        ],
    )
    understanding_b = DocumentUnderstanding(
        document_id=doc_b,
        parties=[
            ExtractedParty.create(
                document_id=doc_b,
                name="Acme Corp",
                role="Employer",
                page_number=1,
                source_span="Acme Corp (Employer)",
            ),
            ExtractedParty.create(
                document_id=doc_b,
                name="John Doe",
                role="Senior Director",
                page_number=1,
                source_span="John Doe (Senior Director)",
            ),
        ],
    )

    findings = ComparisonMatcher.compare_documents(
        doc_ids=[doc_a, doc_b],
        doc_titles=titles,
        extractions={doc_a: understanding_a, doc_b: understanding_b},
    )

    assert len(findings) >= 2
    match_findings = [
        f for f in findings if f.classification == DifferenceClassification.MATCH
    ]
    diff_findings = [
        f for f in findings if f.classification == DifferenceClassification.DIFFERENT
    ]

    assert len(match_findings) == 1
    assert match_findings[0].category == ComparisonCategory.PARTIES
    assert "Consistent Party Designation: Acme Corp" in match_findings[0].title

    assert len(diff_findings) == 1
    assert diff_findings[0].category == ComparisonCategory.PARTIES
    assert "Differing Party Role: John Doe" in diff_findings[0].title
    assert len(diff_findings[0].lawyer_questions) > 0


def test_matcher_dates_inconsistency_and_present_in_one_only() -> None:
    """Test date comparison inconsistency detection and present in one only."""
    doc_a = "doc-a"
    doc_b = "doc-b"
    titles = {doc_a: "Original", doc_b: "Amendment"}

    understanding_a = DocumentUnderstanding(
        document_id=doc_a,
        dates=[
            ExtractedDate.create(
                document_id=doc_a,
                raw_text="January 1, 2026",
                normalized_date="2026-01-01",
                date_type="effective_date",
                description="Effective Date",
                page_number=1,
                source_span="Effective date: January 1, 2026",
            ),
            ExtractedDate.create(
                document_id=doc_a,
                raw_text="December 31, 2026",
                normalized_date="2026-12-31",
                date_type="expiration_date",
                description="Expiration Date",
                page_number=1,
                source_span="Expiration date: December 31, 2026",
            ),
        ],
    )
    understanding_b = DocumentUnderstanding(
        document_id=doc_b,
        dates=[
            ExtractedDate.create(
                document_id=doc_b,
                raw_text="February 1, 2026",
                normalized_date="2026-02-01",
                date_type="effective_date",
                description="Effective Date",
                page_number=1,
                source_span="Effective date: February 1, 2026",
            )
        ],
    )

    findings = ComparisonMatcher.compare_documents(
        doc_ids=[doc_a, doc_b],
        doc_titles=titles,
        extractions={doc_a: understanding_a, doc_b: understanding_b},
    )

    # Inconsistent effective date
    inconsistent = next(
        (
            f
            for f in findings
            if f.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
        ),
        None,
    )
    assert inconsistent is not None
    assert "Potential Date Inconsistency: Effective Date" in inconsistent.title

    # Present in one only expiration date
    one_only = next(
        (
            f
            for f in findings
            if f.classification == DifferenceClassification.PRESENT_IN_ONE_ONLY
        ),
        None,
    )
    assert one_only is not None
    assert "Expiration Date" in one_only.title


def test_matcher_obligations_notice_period_difference() -> None:
    """Test notice period difference extraction between obligations."""
    doc_a = "doc-a"
    doc_b = "doc-b"
    titles = {doc_a: "Offer", doc_b: "Agreement"}

    understanding_a = DocumentUnderstanding(
        document_id=doc_a,
        obligations=[
            ExtractedObligation.create(
                document_id=doc_a,
                obligor="Employee",
                duty="provide 30 days notice prior to resignation",
                trigger="resignation",
                deadline="30 days",
                page_start=1,
                page_end=1,
                source_span="Employee must provide 30 days notice.",
            )
        ],
    )
    understanding_b = DocumentUnderstanding(
        document_id=doc_b,
        obligations=[
            ExtractedObligation.create(
                document_id=doc_b,
                obligor="Employee",
                duty="provide 60 days written notice before termination",
                trigger="termination",
                deadline="60 days",
                page_start=2,
                page_end=2,
                source_span="Employee shall provide 60 days notice.",
            )
        ],
    )

    findings = ComparisonMatcher.compare_documents(
        doc_ids=[doc_a, doc_b],
        doc_titles=titles,
        extractions={doc_a: understanding_a, doc_b: understanding_b},
    )

    notice_findings = [
        f
        for f in findings
        if f.classification == DifferenceClassification.POTENTIAL_INCONSISTENCY
    ]
    assert len(notice_findings) >= 1
    finding = notice_findings[0]
    assert "30 vs 60 Days" in finding.title or "30" in finding.title
    assert len(finding.lawyer_questions) > 0


def test_matcher_clauses_present_in_one_only_safe_wording() -> None:
    """Verify PRESENT_IN_ONE_ONLY safe phrasing without declaring absence."""
    doc_a = "doc-a"
    doc_b = "doc-b"
    titles = {doc_a: "NDA", doc_b: "Amendment"}

    understanding_a = DocumentUnderstanding(
        document_id=doc_a,
        clauses=[
            ExtractedClause.create(
                document_id=doc_a,
                title="Non-Compete Provision",
                category="non_compete",
                clause_identifier="Section 8",
                text="Employee agrees not to compete for 12 months.",
                page_start=3,
                page_end=3,
                source_span="Section 8. Non-Compete.",
            )
        ],
    )
    understanding_b = DocumentUnderstanding(
        document_id=doc_b,
        clauses=[],
    )

    findings = ComparisonMatcher.compare_documents(
        doc_ids=[doc_a, doc_b],
        doc_titles=titles,
        extractions={doc_a: understanding_a, doc_b: understanding_b},
    )

    clause_findings = [
        f
        for f in findings
        if f.classification == DifferenceClassification.PRESENT_IN_ONE_ONLY
    ]
    assert len(clause_findings) == 1
    finding = clause_findings[0]
    assert finding.classification == DifferenceClassification.PRESENT_IN_ONE_ONLY
    # Strict invariant: must state "not identified in the extracted content"
    assert (
        "was identified in NDA but was not identified in the extracted "
        "content of Amendment"
        in finding.description
        or "identified in NDA but was not identified" in finding.description
    )
    assert "does not contain" not in finding.description
