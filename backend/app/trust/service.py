from collections import Counter
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.evidence.service import EvidenceService
from app.trust.classifier import TrustClassifier
from app.trust.models import (
    AssessedClaim,
    DocumentNotFoundError,
    DocumentNotReadyForTrustError,
    DocumentTrustReport,
    InvalidTrustInputError,
    SafetyStatus,
)
from app.trust.repository import TrustRepository, get_trust_repository

MAX_AD_HOC_CLAIMS = 50
MAX_CLAIM_TEXT_LENGTH = 2000


class TrustService:
    """Coordinates document trust evaluation and safety boundaries."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        evidence_service: EvidenceService | None = None,
        trust_repository: TrustRepository | None = None,
        classifier: TrustClassifier | None = None,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._evidence_service = evidence_service or EvidenceService()
        self._trust_repo = trust_repository or get_trust_repository()
        self._classifier = classifier or TrustClassifier()

    def get_document_trust_report(
        self, document_id: str, user_id: str
    ) -> DocumentTrustReport:
        """Generate or retrieve comprehensive trust report for an owned document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForTrustError(
                f"Document is in state '{doc.status.value}', "
                "must be processed and ready."
            )

        # 1. Obtain authoritative evidence report from Phase 7 Evidence Engine
        evidence_report = self._evidence_service.get_document_evidence(
            document_id=document_id, user_id=user_id
        )

        # 2. Evaluate all claims through deterministic TrustClassifier
        assessed_claims: list[AssessedClaim] = []
        for claim in evidence_report.claims:
            assessment = self._classifier.classify_claim(claim)
            assessed_claims.append(
                AssessedClaim(
                    id=claim.id,
                    document_id=document_id,
                    claim_text=claim.claim_text,
                    claim_type=claim.claim_type,
                    trust_assessment=assessment,
                    evidence=claim.evidence,
                )
            )

        # 3. Persist derived assessment snapshot
        self._trust_repo.save_assessments(document_id, assessed_claims)

        # 4. Compute distributions and overall status
        total_claims = len(assessed_claims)
        tier_counts = dict(
            Counter(ac.trust_assessment.trust_tier.value for ac in assessed_claims)
        )
        limitation_counts: dict[str, int] = {}
        for ac in assessed_claims:
            for lim in ac.trust_assessment.limitations:
                limitation_counts[lim.value] = limitation_counts.get(lim.value, 0) + 1

        overall_status = SafetyStatus.SAFE
        if any(
            ac.trust_assessment.safety_status == SafetyStatus.UNSUPPORTED
            for ac in assessed_claims
        ):
            overall_status = SafetyStatus.LIMITED
        if any(
            ac.trust_assessment.professional_review_required for ac in assessed_claims
        ):
            overall_status = SafetyStatus.REVIEW_REQUIRED

        return DocumentTrustReport(
            document_id=document_id,
            assessed_claims=assessed_claims,
            overall_safety_status=overall_status,
            evidence_coverage=evidence_report.coverage.coverage_ratio,
            total_claims=total_claims,
            tier_counts=tier_counts,
            limitation_counts=limitation_counts,
        )

    def assess_ad_hoc_claims(
        self,
        document_id: str,
        user_id: str,
        claims_input: list[dict[str, Any]],
    ) -> list[AssessedClaim]:
        """Assess bounded ad-hoc claims against document evidence."""
        if not isinstance(claims_input, list):
            raise InvalidTrustInputError("Claims payload must be a list.")

        if len(claims_input) > MAX_AD_HOC_CLAIMS:
            raise InvalidTrustInputError(
                f"Exceeded maximum ad-hoc claims limit of {MAX_AD_HOC_CLAIMS}."
            )

        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError("Document not found or access denied.")

        # Re-use evidence validation for ad-hoc claims
        validated_evidence_report = self._evidence_service.validate_ad_hoc_claims(
            document_id=document_id,
            user_id=user_id,
            raw_claims=claims_input,
        )

        results: list[AssessedClaim] = []
        for claim in validated_evidence_report.claims:
            assessment = self._classifier.classify_claim(claim)
            results.append(
                AssessedClaim(
                    id=claim.id,
                    document_id=document_id,
                    claim_text=claim.claim_text,
                    claim_type=claim.claim_type,
                    trust_assessment=assessment,
                    evidence=claim.evidence,
                )
            )

        return results
