import pytest

from app.extraction.models import (
    ClauseCategory,
    DateType,
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
    InvalidExtractionSchemaError,
    ReviewFlagType,
)


def test_extracted_party_validation() -> None:
    party = ExtractedParty.create(
        document_id="doc-123",
        name="Acme Corp",
        role="Employer",
        page_number=1,
        source_span='between Acme Corp ("Employer")',
    )
    assert party.name == "Acme Corp"
    assert party.role == "Employer"
    assert party.page_number == 1
    assert party.document_id == "doc-123"

    # Missing name raises InvalidExtractionSchemaError
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedParty.create(
            document_id="doc-123",
            name="",
            role="Employer",
            page_number=1,
            source_span="test",
        )

    # Invalid page number
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedParty.create(
            document_id="doc-123",
            name="Acme Corp",
            role="Employer",
            page_number=0,
            source_span="test",
        )


def test_extracted_clause_validation() -> None:
    clause = ExtractedClause.create(
        document_id="doc-123",
        clause_identifier="Clause-1",
        title="Payment Terms",
        category="payment",
        text=(
            "The tenant shall pay monthly rent of $2,000 on or before the 1st of each"
            " month."
        ),
        page_start=1,
        page_end=1,
        source_span="1. Payment Terms. The tenant shall pay...",
    )
    assert clause.category == ClauseCategory.PAYMENT.value
    assert clause.title == "Payment Terms"

    # Empty title raises
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedClause.create(
            document_id="doc-123",
            clause_identifier="1",
            title="",
            category="payment",
            text="text",
            page_start=1,
            page_end=1,
            source_span="span",
        )

    # Inverted page range raises
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedClause.create(
            document_id="doc-123",
            clause_identifier="1",
            title="Title",
            category="payment",
            text="text",
            page_start=2,
            page_end=1,
            source_span="span",
        )


def test_extracted_obligation_validation() -> None:
    obligation = ExtractedObligation.create(
        document_id="doc-123",
        obligor="Tenant",
        duty="shall maintain comprehensive property insurance",
        trigger="Upon execution of this lease",
        deadline="within 14 days",
        page_start=2,
        page_end=2,
        source_span=(
            "Upon execution, Tenant shall maintain comprehensive property insurance"
            " within 14 days."
        ),
    )
    assert obligation.obligor == "Tenant"
    assert obligation.trigger == "Upon execution of this lease"
    assert obligation.deadline == "within 14 days"

    # Empty duty raises
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedObligation.create(
            document_id="doc-123",
            obligor="Tenant",
            duty="",
            trigger=None,
            deadline=None,
            page_start=1,
            page_end=1,
            source_span="span",
        )


def test_extracted_date_validation() -> None:
    dt = ExtractedDate.create(
        document_id="doc-123",
        date_type="effective_date",
        raw_text="January 15, 2026",
        normalized_date="2026-01-15",
        description="Agreement commencement date",
        page_number=1,
        source_span="This Agreement is effective as of January 15, 2026.",
    )
    assert dt.date_type == DateType.EFFECTIVE_DATE.value
    assert dt.normalized_date == "2026-01-15"

    # Empty raw text raises
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedDate.create(
            document_id="doc-123",
            date_type="effective_date",
            raw_text="",
            normalized_date=None,
            description="desc",
            page_number=1,
            source_span="span",
        )


def test_extracted_review_flag_validation() -> None:
    flag = ExtractedReviewFlag.create(
        document_id="doc-123",
        flag_type="restrictive_covenant",
        title="Restrictive Covenant (Non-Compete)",
        description=(
            "The agreement includes a 24-month non-compete clause. Consulting"
            " independent legal counsel regarding enforceability is recommended."
        ),
        severity="medium",
        page_start=3,
        page_end=3,
        source_span="Employee shall not engage in competing business for 24 months.",
    )
    assert flag.flag_type == ReviewFlagType.RESTRICTIVE_COVENANT.value
    assert flag.severity == "medium"

    # Empty title raises
    with pytest.raises(InvalidExtractionSchemaError):
        ExtractedReviewFlag.create(
            document_id="doc-123",
            flag_type="ambiguous_term",
            title="",
            description="desc",
            severity="low",
            page_start=1,
            page_end=1,
            source_span="span",
        )


def test_document_understanding_serialization() -> None:
    party = ExtractedParty.create(
        "doc-1", "Alpha LLC", "Client", 1, "Alpha LLC (Client)"
    )
    clause = ExtractedClause.create(
        "doc-1",
        "1",
        "Services",
        "general",
        "Alpha LLC will receive services",
        1,
        1,
        "Services",
    )
    understanding = DocumentUnderstanding(
        document_id="doc-1",
        parties=[party],
        clauses=[clause],
        obligations=[],
        dates=[],
        review_flags=[],
        provider_info={"provider": "test"},
    )
    data = understanding.to_dict()
    assert data["document_id"] == "doc-1"
    assert len(data["parties"]) == 1
    assert len(data["clauses"]) == 1
    assert data["counts"]["parties"] == 1
    assert data["counts"]["clauses"] == 1
    assert data["counts"]["obligations"] == 0
