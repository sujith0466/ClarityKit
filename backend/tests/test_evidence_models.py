import pytest

from app.evidence.models import (
    Claim,
    ClaimType,
    DocumentEvidenceReport,
    EvidenceCoverage,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
    InvalidEvidenceInputError,
)


def test_claim_creation_and_serialization() -> None:
    ref = EvidenceReference(
        document_id="doc-1",
        page_start=1,
        page_end=1,
        source_span="Acme Corp agrees to pay $1,000.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim = Claim.create(
        document_id="doc-1",
        claim_text="Acme Corp agrees to pay $1,000.",
        claim_type=ClaimType.OBLIGATION,
        evidence=ref,
        entity_id="obl-1",
    )

    assert claim.claim_type == ClaimType.OBLIGATION
    assert claim.validation_status == EvidenceValidationStatus.VALID
    assert claim.evidence is not None
    assert claim.evidence.match_type == EvidenceMatchType.EXACT

    data = claim.to_dict()
    assert data["claim_text"] == "Acme Corp agrees to pay $1,000."
    assert data["claim_type"] == "obligation"
    assert data["validation_status"] == "VALID"
    assert data["evidence"]["page_start"] == 1


def test_claim_without_evidence_defaults_to_invalid() -> None:
    claim = Claim.create(
        document_id="doc-1",
        claim_text="Unreferenced legal claim",
        claim_type=ClaimType.GENERAL_FACT,
        evidence=None,
    )
    assert claim.validation_status == EvidenceValidationStatus.INVALID
    assert claim.evidence is None


def test_claim_empty_text_raises_error() -> None:
    with pytest.raises(InvalidEvidenceInputError):
        Claim.create(
            document_id="doc-1",
            claim_text="   ",
            claim_type=ClaimType.PARTY,
        )


def test_evidence_coverage_calculation_exact_ratio() -> None:
    claims = [
        Claim.create(
            document_id="doc-1",
            claim_text=f"Claim {i}",
            claim_type=ClaimType.PARTY,
            evidence=EvidenceReference(
                document_id="doc-1",
                page_start=1,
                page_end=1,
                source_span=f"Span {i}",
                validation_status=(
                    EvidenceValidationStatus.VALID
                    if i < 9
                    else EvidenceValidationStatus.INVALID
                ),
            ),
        )
        for i in range(10)
    ]

    cov = EvidenceCoverage.calculate(claims)
    assert cov.total_claims == 10
    assert cov.valid_claims == 9
    assert cov.invalid_claims == 1
    assert cov.unverified_claims == 0
    assert cov.coverage_ratio == 0.9
    assert cov.coverage_percentage == 90.0
    assert cov.is_fully_covered is False


def test_evidence_coverage_full_coverage() -> None:
    claims = [
        Claim.create(
            document_id="doc-1",
            claim_text=f"Claim {i}",
            claim_type=ClaimType.PARTY,
            evidence=EvidenceReference(
                document_id="doc-1",
                page_start=1,
                page_end=1,
                source_span=f"Span {i}",
                validation_status=EvidenceValidationStatus.VALID,
            ),
        )
        for i in range(5)
    ]

    cov = EvidenceCoverage.calculate(claims)
    assert cov.total_claims == 5
    assert cov.valid_claims == 5
    assert cov.coverage_ratio == 1.0
    assert cov.is_fully_covered is True


def test_evidence_coverage_empty_claims() -> None:
    cov = EvidenceCoverage.calculate([])
    assert cov.total_claims == 0
    assert cov.valid_claims == 0
    assert cov.coverage_ratio == 0.0
    assert cov.is_fully_covered is False


def test_document_evidence_report_serialization() -> None:
    report = DocumentEvidenceReport(
        document_id="doc-123",
        claims=[],
        coverage=EvidenceCoverage.calculate([]),
    )
    data = report.to_dict()
    assert data["document_id"] == "doc-123"
    assert "Citation validity indicates" in data["disclaimer"]
