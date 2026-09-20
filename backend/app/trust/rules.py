import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceValidationStatus,
)
from app.trust.models import (
    LimitationType,
    SafetyStatus,
    TrustAssessment,
    TrustTier,
)


@dataclass
class TrustRule:
    """Deterministic, auditable safety and classification rule."""

    rule_id: str
    name: str
    priority: int  # Lower number = higher precedence
    predicate: Callable[[Claim, dict[str, Any]], bool]
    evaluator: Callable[[Claim, dict[str, Any]], TrustAssessment]


ENFORCEABILITY_PATTERNS = [
    re.compile(
        r"\b(enforceab|legally\s+enforceable|is\s+.*enforceable|binding|"
        r"will\s+i\s+win|should\s+i\s+sign|legal\s+validity|null\s+and\s+void|"
        r"unlawful|prohibited\s+by\s+law|statute\s+of\s+limitations)\b",
        re.IGNORECASE,
    ),
]

JURISDICTION_PATTERNS = [
    re.compile(
        r"\b(under\s+california\s+law|under\s+new\s+york\s+law|"
        r"jurisdiction\s+governs|state\s+statute|local\s+ordinance|"
        r"federal\s+law\s+requires|current\s+law)\b",
        re.IGNORECASE,
    ),
]

INTERPRETATION_PATTERNS = [
    re.compile(
        r"\b(appears\s+to\s+mean|interpreted\s+as|suggests\s+that|"
        r"implies\s+that|likely\s+means|intended\s+to)\b",
        re.IGNORECASE,
    ),
]


def _has_pattern(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def _is_enforceability_claim(claim: Claim, ctx: dict[str, Any]) -> bool:
    return _has_pattern(claim.claim_text, ENFORCEABILITY_PATTERNS) or bool(
        ctx.get("is_enforceability_query", False)
    )


def _eval_enforceability(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
        safety_status=SafetyStatus.REVIEW_REQUIRED,
        evidence_required=False,
        evidence_valid=False,
        professional_review_required=True,
        limitations=[
            LimitationType.LEGAL_ENFORCEABILITY,
            LimitationType.PROFESSIONAL_JUDGMENT,
        ],
        reasoning_summary=(
            "Legal enforceability, bindingness, or dispute outcome depends "
            "on external statutory law, judicial precedent, and facts outside "
            "the document. Professional legal review is required."
        ),
    )


def _is_jurisdiction_dependent(claim: Claim, ctx: dict[str, Any]) -> bool:
    return _has_pattern(claim.claim_text, JURISDICTION_PATTERNS) or bool(
        ctx.get("requires_jurisdiction", False)
    )


def _eval_jurisdiction(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
        safety_status=SafetyStatus.REVIEW_REQUIRED,
        evidence_required=False,
        evidence_valid=False,
        professional_review_required=True,
        limitations=[
            LimitationType.MISSING_JURISDICTION,
            LimitationType.CURRENT_LAW_REQUIRED,
        ],
        reasoning_summary=(
            "The statement depends on specific jurisdictional rules or current "
            "statutory requirements not established solely by document text."
        ),
    )


def _is_document_specific_claim(claim: Claim, ctx: dict[str, Any]) -> bool:
    if claim.claim_type == ClaimType.GENERAL_FACT and claim.evidence is None:
        return False
    return True


def _has_invalid_or_missing_evidence(claim: Claim, ctx: dict[str, Any]) -> bool:
    if not _is_document_specific_claim(claim, ctx):
        return False
    if claim.evidence is None:
        return True
    return claim.evidence.validation_status != EvidenceValidationStatus.VALID


def _eval_missing_or_invalid_evidence(
    claim: Claim, ctx: dict[str, Any]
) -> TrustAssessment:
    if claim.evidence is None:
        limitations = [LimitationType.MISSING_EVIDENCE]
        reason = "Document-specific claim lacks supporting evidence citations."
    elif claim.evidence.document_id != claim.document_id:
        limitations = [LimitationType.CROSS_DOCUMENT_EVIDENCE]
        reason = "Evidence citation references an external or mismatched document."
    else:
        limitations = [LimitationType.INVALID_EVIDENCE]
        reason = (
            "Evidence citation failed mechanical verification "
            "against document page text."
        )

    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
        safety_status=SafetyStatus.UNSUPPORTED,
        evidence_required=True,
        evidence_valid=False,
        professional_review_required=True,
        limitations=limitations,
        reasoning_summary=reason,
    )


def _is_materially_ambiguous(claim: Claim, ctx: dict[str, Any]) -> bool:
    if bool(ctx.get("is_ambiguous", False)):
        return True
    if claim.claim_type == ClaimType.REVIEW_FLAG:
        flag_type = str(ctx.get("flag_type", "")).lower()
        if "ambiguous" in flag_type:
            return True
    return False


def _eval_ambiguous_language(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    has_valid_ev = (
        claim.evidence is not None
        and claim.evidence.validation_status == EvidenceValidationStatus.VALID
    )
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.INTERPRETATION,
        safety_status=SafetyStatus.REVIEW_REQUIRED,
        evidence_required=True,
        evidence_valid=has_valid_ev,
        professional_review_required=True,
        limitations=[
            LimitationType.AMBIGUOUS_LANGUAGE,
            LimitationType.PROFESSIONAL_JUDGMENT,
        ],
        reasoning_summary=(
            "The referenced clause contains ambiguous or non-standard terms. "
            "Meaning represents an interpretation subject to legal review."
        ),
    )


def _is_interpretation(claim: Claim, ctx: dict[str, Any]) -> bool:
    if _has_pattern(claim.claim_text, INTERPRETATION_PATTERNS):
        return True
    return bool(ctx.get("is_interpretation", False))


def _eval_interpretation(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    has_valid_ev = (
        claim.evidence is not None
        and claim.evidence.validation_status == EvidenceValidationStatus.VALID
    )
    limitations = [] if has_valid_ev else [LimitationType.MISSING_EVIDENCE]
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.INTERPRETATION,
        safety_status=SafetyStatus.LIMITED
        if has_valid_ev
        else SafetyStatus.UNSUPPORTED,
        evidence_required=True,
        evidence_valid=has_valid_ev,
        professional_review_required=not has_valid_ev,
        limitations=limitations,
        reasoning_summary=(
            "This statement explains or interprets document language rather "
            "than stating a verbatim factual term."
        ),
    )


def _is_valid_document_fact(claim: Claim, ctx: dict[str, Any]) -> bool:
    if claim.evidence is None:
        return False
    return (
        claim.evidence.validation_status == EvidenceValidationStatus.VALID
        and claim.evidence.document_id == claim.document_id
    )


def _eval_document_fact(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
        evidence_required=True,
        evidence_valid=True,
        professional_review_required=False,
        limitations=[],
        reasoning_summary=(
            "Claim is directly supported by mechanically verified source spans "
            "within the authoritative document."
        ),
    )


def _is_general_information(claim: Claim, ctx: dict[str, Any]) -> bool:
    return claim.claim_type == ClaimType.GENERAL_FACT or bool(
        ctx.get("is_general_info", False)
    )


def _eval_general_information(claim: Claim, ctx: dict[str, Any]) -> TrustAssessment:
    return TrustAssessment(
        claim_id=claim.id,
        trust_tier=TrustTier.GENERAL_INFORMATION,
        safety_status=SafetyStatus.SAFE,
        evidence_required=False,
        evidence_valid=False,
        professional_review_required=False,
        limitations=[],
        reasoning_summary=(
            "General educational information describing legal concepts without "
            "asserting facts about this specific document."
        ),
    )


def get_default_trust_rules() -> list[TrustRule]:
    """Return the ordered deterministic rule set for Phase 8."""
    return [
        TrustRule(
            rule_id="RULE-10-ENFORCEABILITY",
            name="Enforceability & Legal Outcome Rule",
            priority=10,
            predicate=_is_enforceability_claim,
            evaluator=_eval_enforceability,
        ),
        TrustRule(
            rule_id="RULE-20-JURISDICTION",
            name="Jurisdiction & Current Law Dependency Rule",
            priority=20,
            predicate=_is_jurisdiction_dependent,
            evaluator=_eval_jurisdiction,
        ),
        TrustRule(
            rule_id="RULE-30-EVIDENCE-VALIDATION",
            name="Missing / Invalid Evidence Escalation Rule",
            priority=30,
            predicate=_has_invalid_or_missing_evidence,
            evaluator=_eval_missing_or_invalid_evidence,
        ),
        TrustRule(
            rule_id="RULE-40-AMBIGUITY",
            name="Material Ambiguity Rule",
            priority=40,
            predicate=_is_materially_ambiguous,
            evaluator=_eval_ambiguous_language,
        ),
        TrustRule(
            rule_id="RULE-50-INTERPRETATION",
            name="Document Interpretation Rule",
            priority=50,
            predicate=_is_interpretation,
            evaluator=_eval_interpretation,
        ),
        TrustRule(
            rule_id="RULE-60-DOCUMENT-FACT",
            name="Valid Document Fact Rule",
            priority=60,
            predicate=_is_valid_document_fact,
            evaluator=_eval_document_fact,
        ),
        TrustRule(
            rule_id="RULE-70-GENERAL-INFO",
            name="General Legal Information Rule",
            priority=70,
            predicate=_is_general_information,
            evaluator=_eval_general_information,
        ),
    ]
