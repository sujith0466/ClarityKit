from app.evidence.models import EvidenceMatchType, EvidenceValidationStatus
from app.evidence.resolver import SourceSpanResolver


def test_resolve_exact_match_single_page() -> None:
    page_text = (
        "This Commercial Lease Agreement is entered into between "
        "Acme Corp (Landlord) and Beta LLC (Tenant)."
    )
    res = SourceSpanResolver.resolve_single_page(
        page_text=page_text,
        source_span="Acme Corp (Landlord)",
    )

    assert res.status == EvidenceValidationStatus.VALID
    assert res.match_type == EvidenceMatchType.EXACT
    assert res.char_start is not None
    assert res.char_end is not None
    assert page_text[res.char_start : res.char_end] == "Acme Corp (Landlord)"
    assert res.source_text == "Acme Corp (Landlord)"
    assert res.reason is None


def test_resolve_normalized_whitespace_single_page() -> None:
    page_text = (
        "Tenant shall pay to Landlord\n\nthe sum of   $3,500   per month\nin advance."
    )
    res = SourceSpanResolver.resolve_single_page(
        page_text=page_text,
        source_span=(
            "Tenant shall pay to Landlord the sum of $3,500 per month in advance."
        ),
    )

    assert res.status == EvidenceValidationStatus.VALID
    assert res.match_type == EvidenceMatchType.NORMALIZED_WHITESPACE
    assert res.char_start is not None
    assert res.char_end is not None
    assert res.source_text == (
        "Tenant shall pay to Landlord\n\nthe sum of   $3,500   per month\nin advance."
    )


def test_resolve_unicode_whitespace_single_page() -> None:
    page_text = "Base\u00a0Rent\u200b:\u00a0$5,000 per calendar month."
    res = SourceSpanResolver.resolve_single_page(
        page_text=page_text,
        source_span="Base Rent: $5,000 per calendar month.",
    )

    assert res.status == EvidenceValidationStatus.VALID
    assert res.match_type == EvidenceMatchType.NORMALIZED_WHITESPACE


def test_resolve_cross_page_contiguous() -> None:
    page_texts = {
        1: "Parties\nThis agreement is made between Party A and Party B.",
        2: (
            "Section 5: Termination.\nEither party may terminate this agreement "
            "upon providing"
        ),
        3: "thirty (30) days' prior written notice to the other party.",
        4: "Section 6: Governing Law.\nThis agreement is governed by California law.",
    }

    res = SourceSpanResolver.resolve_cross_page(
        page_texts=page_texts,
        page_start=2,
        page_end=3,
        source_span=(
            "Either party may terminate this agreement upon providing "
            "thirty (30) days' prior written notice"
        ),
    )

    assert res.status == EvidenceValidationStatus.VALID
    assert res.match_type == EvidenceMatchType.CROSS_PAGE
    assert res.reason is None


def test_resolve_cross_page_fails_when_intermediate_page_missing() -> None:
    page_texts = {
        1: "Page 1 text",
        3: "Page 3 text",
    }

    res = SourceSpanResolver.resolve_cross_page(
        page_texts=page_texts,
        page_start=1,
        page_end=3,
        source_span="Page 1 text Page 3 text",
    )

    assert res.status == EvidenceValidationStatus.INVALID
    assert res.reason == "PAGE_2_NOT_FOUND"


def test_resolve_cross_page_fails_when_match_does_not_span_claimed_range() -> None:
    page_texts = {
        1: "Page 1 heading and intro.",
        2: "Tenant shall pay rent of $1,000 on the first of each month.",
    }

    res = SourceSpanResolver.resolve_cross_page(
        page_texts=page_texts,
        page_start=1,
        page_end=2,
        source_span="Tenant shall pay rent of $1,000",
    )

    assert res.status == EvidenceValidationStatus.INVALID
    assert "PAGE_RANGE_MISMATCH" in (res.reason or "")


def test_resolve_span_not_found_fails() -> None:
    page_text = "Tenant shall pay rent on the 1st of the month."
    res = SourceSpanResolver.resolve_single_page(
        page_text=page_text,
        source_span="Tenant shall pay rent on the 15th of the month.",
    )

    assert res.status == EvidenceValidationStatus.INVALID
    assert res.match_type == EvidenceMatchType.UNMATCHED
    assert res.reason == "SPAN_NOT_FOUND_ON_PAGE"


def test_resolve_empty_and_whitespace_only_spans_fail() -> None:
    res = SourceSpanResolver.resolve_single_page(
        page_text="Some valid document text",
        source_span="   ",
    )

    assert res.status == EvidenceValidationStatus.INVALID
    assert res.reason == "EMPTY_SOURCE_SPAN"


def test_resolve_tampered_numbers_or_words_fail() -> None:
    page_text = "Executive non-compete duration is twelve (12) months."
    res = SourceSpanResolver.resolve_single_page(
        page_text=page_text,
        source_span="Executive non-compete duration is twenty-four (24) months.",
    )

    assert res.status == EvidenceValidationStatus.INVALID
    assert res.match_type == EvidenceMatchType.UNMATCHED
