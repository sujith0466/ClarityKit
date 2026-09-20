from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.trust.classifier import TrustClassifier
from app.trust.models import (
    LimitationType,
    SafetyStatus,
    TrustTier,
)


def test_valid_document_fact_classification() -> None:
    classifier = TrustClassifier()
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=1,
        page_end=1,
        source_span="Rent is $1500 per month payable on the 1st.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim = Claim(
        id="c-1",
        document_id="doc-1",
        claim_text="Rent is $1500 per month payable on the 1st.",
        claim_type=ClaimType.OBLIGATION,
        evidence=ev,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.DOCUMENT_FACT
    assert assessment.safety_status == SafetyStatus.SAFE
    assert assessment.evidence_valid is True
    assert assessment.professional_review_required is False
    assert assessment.limitations == []


def test_missing_evidence_escalation() -> None:
    classifier = TrustClassifier()
    claim = Claim(
        id="c-2",
        document_id="doc-1",
        claim_text="Tenant must deposit $3000 upon execution.",
        claim_type=ClaimType.OBLIGATION,
        evidence=None,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert assessment.safety_status == SafetyStatus.UNSUPPORTED
    assert assessment.evidence_valid is False
    assert assessment.professional_review_required is True
    assert LimitationType.MISSING_EVIDENCE in assessment.limitations


def test_invalid_evidence_escalation() -> None:
    classifier = TrustClassifier()
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=1,
        page_end=1,
        source_span="Fabricated span",
        match_type=EvidenceMatchType.UNMATCHED,
        validation_status=EvidenceValidationStatus.INVALID,
        validation_reason="Span not found in page text",
    )
    claim = Claim(
        id="c-3",
        document_id="doc-1",
        claim_text="Landlord may enter without notice.",
        claim_type=ClaimType.CLAUSE,
        evidence=ev,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert assessment.safety_status == SafetyStatus.UNSUPPORTED
    assert assessment.evidence_valid is False
    assert LimitationType.INVALID_EVIDENCE in assessment.limitations


def test_enforceability_question_escalates_to_professional_review() -> None:
    classifier = TrustClassifier()
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=2,
        page_end=2,
        source_span="Employee agrees not to compete for 5 years worldwide.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim = Claim(
        id="c-4",
        document_id="doc-1",
        claim_text="Is this 5-year non-compete covenant legally enforceable?",
        claim_type=ClaimType.REVIEW_FLAG,
        evidence=ev,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert assessment.safety_status == SafetyStatus.REVIEW_REQUIRED
    assert assessment.professional_review_required is True
    assert LimitationType.LEGAL_ENFORCEABILITY in assessment.limitations
    assert LimitationType.PROFESSIONAL_JUDGMENT in assessment.limitations


def test_jurisdiction_dependency_escalation() -> None:
    classifier = TrustClassifier()
    claim = Claim(
        id="c-5",
        document_id="doc-1",
        claim_text="Under California law, this non-compete is void.",
        claim_type=ClaimType.GENERAL_FACT,
        evidence=None,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert assessment.safety_status == SafetyStatus.REVIEW_REQUIRED
    assert LimitationType.MISSING_JURISDICTION in assessment.limitations
    assert LimitationType.CURRENT_LAW_REQUIRED in assessment.limitations


def test_interpretation_with_valid_evidence() -> None:
    classifier = TrustClassifier()
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=1,
        page_end=1,
        source_span="Either party may terminate upon 30 days notice.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim = Claim(
        id="c-6",
        document_id="doc-1",
        claim_text=(
            "This clause appears to mean that termination requires "
            "30 days written notice."
        ),
        claim_type=ClaimType.CLAUSE,
        evidence=ev,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.INTERPRETATION
    assert assessment.safety_status == SafetyStatus.LIMITED
    assert assessment.evidence_valid is True
    assert assessment.professional_review_required is False


def test_general_educational_information() -> None:
    classifier = TrustClassifier()
    claim = Claim(
        id="c-7",
        document_id="doc-1",
        claim_text=(
            "NDAs typically protect confidential proprietary business records."
        ),
        claim_type=ClaimType.GENERAL_FACT,
        evidence=None,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.GENERAL_INFORMATION
    assert assessment.safety_status == SafetyStatus.SAFE
    assert assessment.evidence_required is False
    assert assessment.limitations == []


def test_restrictive_covenant_direct_statement_is_document_fact() -> None:
    classifier = TrustClassifier()
    ev = EvidenceReference(
        document_id="doc-1",
        page_start=3,
        page_end=3,
        source_span="Recipient shall not solicit employees for 12 months.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim = Claim(
        id="c-8",
        document_id="doc-1",
        claim_text="The agreement contains a 12-month non-solicitation restriction.",
        claim_type=ClaimType.REVIEW_FLAG,
        evidence=ev,
    )
    assessment = classifier.classify_claim(claim)
    assert assessment.trust_tier == TrustTier.DOCUMENT_FACT
    assert assessment.safety_status == SafetyStatus.SAFE
