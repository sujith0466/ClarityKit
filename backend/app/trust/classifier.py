from typing import Any

from app.evidence.models import Claim
from app.trust.models import (
    LimitationType,
    SafetyStatus,
    TrustAssessment,
    TrustTier,
)
from app.trust.rules import TrustRule, get_default_trust_rules


class TrustClassifier:
    """Deterministic classifier evaluating claims against safety rules."""

    def __init__(self, rules: list[TrustRule] | None = None) -> None:
        self._rules = sorted(
            rules if rules is not None else get_default_trust_rules(),
            key=lambda r: r.priority,
        )

    def classify_claim(
        self, claim: Claim, context: dict[str, Any] | None = None
    ) -> TrustAssessment:
        """Classify a single claim using deterministic rule precedence."""
        ctx = context or {}

        for rule in self._rules:
            if rule.predicate(claim, ctx):
                return rule.evaluator(claim, ctx)

        # Fallback for unhandled edge cases: fail safe to Professional Review
        return TrustAssessment(
            claim_id=claim.id,
            trust_tier=TrustTier.PROFESSIONAL_REVIEW_NEEDED,
            safety_status=SafetyStatus.REVIEW_REQUIRED,
            evidence_required=True,
            evidence_valid=False,
            professional_review_required=True,
            limitations=[LimitationType.PROFESSIONAL_JUDGMENT],
            reasoning_summary=(
                "No specific safety rule matched. Defaulted to professional review."
            ),
        )

    def classify_batch(
        self,
        claims: list[Claim],
        contexts: dict[str, dict[str, Any]] | None = None,
    ) -> list[TrustAssessment]:
        """Classify a collection of claims."""
        ctx_map = contexts or {}
        return [self.classify_claim(c, ctx_map.get(c.id, {})) for c in claims]
