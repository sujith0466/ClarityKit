from app.evidence.models import (
    ClaimType,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.trust.models import (
    AssessedClaim,
    DocumentTrustReport,
    LimitationType,
    SafetyStatus,
    TrustAssessment,
    TrustTier,
)


def test_trust_tier_values() -> None:
    assert TrustTier.DOCUMENT_FACT.value == "DOCUMENT_FACT"
    assert TrustTier.GENERAL_INFORMATION.value == "GENERAL_INFORMATION"
    assert TrustTier.INTERPRETATION.value == "INTERPRETATION"
    assert TrustTier.PROFESSIONAL_REVIEW_NEEDED.value == "PROFESSIONAL_REVIEW_NEEDED"


def test_safety_status_values() -> None:
    assert SafetyStatus.SAFE.value == "SAFE"
    assert SafetyStatus.LIMITED.value == "LIMITED"
    assert SafetyStatus.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
    assert SafetyStatus.UNSUPPORTED.value == "UNSUPPORTED"


def test_trust_assessment_serialization() -> None:
    assessment = TrustAssessment(
        claim_id="claim-1",
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
        evidence_required=True,
        evidence_valid=True,
        professional_review_required=False,
        limitations=[],
        reasoning_summary="Valid fact",
    )
    d = assessment.to_dict()
    assert d["claim_id"] == "claim-1"
    assert d["trust_tier"] == "DOCUMENT_FACT"
    assert d["safety_status"] == "SAFE"
    assert d["evidence_valid"] is True
    assert d["limitations"] == []

    deserialized = TrustAssessment.from_dict(d)
    assert deserialized.claim_id == assessment.claim_id
    assert deserialized.trust_tier == TrustTier.DOCUMENT_FACT
    assert deserialized.safety_status == SafetyStatus.SAFE


def test_assessed_claim_serialization() -> None:
    assessment = TrustAssessment(
        claim_id="claim-2",
        trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
        safety_status=SafetyStatus.UNSUPPORTED,
        evidence_required=True,
        evidence_valid=False,
        professional_review_required=True,
        limitations=[LimitationType.MISSING_EVIDENCE],
        reasoning_summary="Missing evidence",
    )
    claim = AssessedClaim(
        id="ac-2",
        document_id="doc-123",
        claim_text="The tenant shall pay $2000.",
        claim_type=ClaimType.OBLIGATION,
        trust_assessment=assessment,
        evidence=None,
    )
    d = claim.to_dict()
    assert d["id"] == "ac-2"
    assert d["document_id"] == "doc-123"
    assert d["claim_type"] == "obligation"
    assert d["trust_assessment"]["trust_tier"] == "PROFESSIONAL_REVIEW_NEEDED"

    rebuilt = AssessedClaim.from_dict(d)
    assert rebuilt.id == "ac-2"
    assert rebuilt.claim_type == ClaimType.OBLIGATION
    assert rebuilt.trust_assessment.limitations == [LimitationType.MISSING_EVIDENCE]


def test_document_trust_report_serialization() -> None:
    assessment = TrustAssessment(
        claim_id="c-1",
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
        evidence_required=True,
        evidence_valid=True,
        professional_review_required=False,
    )
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=1,
        page_end=1,
        source_span="Acme Corp",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    assessed_claim = AssessedClaim(
        id="ac-1",
        document_id="doc-1",
        claim_text="Acme Corp is a party",
        claim_type=ClaimType.PARTY,
        trust_assessment=assessment,
        evidence=ev,
    )
    report = DocumentTrustReport(
        document_id="doc-1",
        assessed_claims=[assessed_claim],
        overall_safety_status=SafetyStatus.SAFE,
        evidence_coverage=1.0,
        total_claims=1,
        tier_counts={"DOCUMENT_FACT": 1},
        limitation_counts={},
    )
    data = report.to_dict()
    assert data["document_id"] == "doc-1"
    assert data["overall_safety_status"] == "SAFE"
    assert data["evidence_coverage"] == 1.0
    assert len(data["assessed_claims"]) == 1
    assert "legal advice" in data["disclaimer"].lower()
