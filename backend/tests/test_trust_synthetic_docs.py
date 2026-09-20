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


def test_synthetic_employment_agreement_trust_evaluation() -> None:
    classifier = TrustClassifier()

    # 1. Fact: Base salary
    ev_salary = EvidenceReference(
        document_id="emp-1",
        page_start=1,
        page_end=1,
        source_span="Base salary shall be $120,000 per annum.",
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim_salary = Claim(
        id="c-sal",
        document_id="emp-1",
        claim_text="The employee receives a base salary of $120,000 per annum.",
        claim_type=ClaimType.OBLIGATION,
        evidence=ev_salary,
    )
    res_salary = classifier.classify_claim(claim_salary)
    assert res_salary.trust_tier == TrustTier.DOCUMENT_FACT
    assert res_salary.safety_status == SafetyStatus.SAFE

    # 2. Interpretation: Discretionary bonus
    ev_bonus = EvidenceReference(
        document_id="emp-1",
        page_start=2,
        page_end=2,
        source_span=(
            "Discretionary bonuses may be granted at company's sole discretion."
        ),
        match_type=EvidenceMatchType.EXACT,
        validation_status=EvidenceValidationStatus.VALID,
    )
    claim_bonus = Claim(
        id="c-bonus",
        document_id="emp-1",
        claim_text=(
            "The wording appears to mean that bonus awards are entirely "
            "at the company's discretion."
        ),
        claim_type=ClaimType.CLAUSE,
        evidence=ev_bonus,
    )
    res_bonus = classifier.classify_claim(claim_bonus)
    assert res_bonus.trust_tier == TrustTier.INTERPRETATION
    assert res_bonus.safety_status == SafetyStatus.LIMITED

    # 3. Professional Review: Enforceability of non-compete
    claim_enforceability = Claim(
        id="c-enf",
        document_id="emp-1",
        claim_text="Is this 2-year post-termination restriction enforceable?",
        claim_type=ClaimType.REVIEW_FLAG,
        evidence=ev_bonus,
    )
    res_enf = classifier.classify_claim(claim_enforceability)
    assert res_enf.trust_tier == TrustTier.PROFESSIONAL_REVIEW_NEEDED
    assert res_enf.safety_status == SafetyStatus.REVIEW_REQUIRED
    assert res_enf.professional_review_required is True
    assert LimitationType.LEGAL_ENFORCEABILITY in res_enf.limitations
