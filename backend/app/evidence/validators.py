import logging

from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceCoverage,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.evidence.resolver import SourceSpanResolver
from app.extraction.models import DocumentUnderstanding

logger = logging.getLogger(__name__)


class EvidenceValidator:
    """Validates claims against authoritative document page texts."""

    @staticmethod
    def validate_claim(claim: Claim, page_texts: dict[int, str]) -> Claim:
        """Validate a single claim against authoritative page texts."""
        if claim.evidence is None:
            claim.validation_status = EvidenceValidationStatus.INVALID
            return claim

        ref = claim.evidence
        res = SourceSpanResolver.resolve(
            page_texts=page_texts,
            page_start=ref.page_start,
            page_end=ref.page_end,
            source_span=ref.source_span,
        )

        ref.validation_status = res.status
        ref.match_type = res.match_type
        ref.char_start = res.char_start
        ref.char_end = res.char_end
        ref.source_text = res.source_text
        ref.validation_reason = res.reason

        claim.validation_status = res.status
        return claim

    @classmethod
    def validate_claims(
        cls, claims: list[Claim], page_texts: dict[int, str]
    ) -> tuple[list[Claim], EvidenceCoverage]:
        """Validate a list of claims and calculate deterministic coverage."""
        validated_claims = [cls.validate_claim(c, page_texts) for c in claims]
        coverage = EvidenceCoverage.calculate(validated_claims)
        return validated_claims, coverage

    @staticmethod
    def claims_from_understanding(
        document_id: str, understanding: DocumentUnderstanding
    ) -> list[Claim]:
        """Transform Phase 6 extraction entities into evidence-backed claims."""
        claims: list[Claim] = []

        for p in understanding.parties:
            ref = EvidenceReference(
                document_id=document_id,
                page_start=p.page_number,
                page_end=p.page_number,
                source_span=p.source_span,
                section="Parties",
            )
            claim = Claim.create(
                document_id=document_id,
                claim_text=f"Party: {p.name} (Role: {p.role})",
                claim_type=ClaimType.PARTY,
                evidence=ref,
                entity_id=p.id,
            )
            claims.append(claim)

        for c in understanding.clauses:
            ref = EvidenceReference(
                document_id=document_id,
                page_start=c.page_start,
                page_end=c.page_end,
                source_span=c.source_span,
                section=c.clause_identifier,
                clause_id=c.id,
            )
            claim = Claim.create(
                document_id=document_id,
                claim_text=(
                    f"Clause {c.clause_identifier}: {c.title} (Category: {c.category})"
                ),
                claim_type=ClaimType.CLAUSE,
                evidence=ref,
                entity_id=c.id,
            )
            claims.append(claim)

        for o in understanding.obligations:
            ref = EvidenceReference(
                document_id=document_id,
                page_start=o.page_start,
                page_end=o.page_end,
                source_span=o.source_span,
                clause_id=o.clause_id,
            )
            details = f"Obligor: {o.obligor} | Duty: {o.duty}"
            if o.deadline:
                details += f" | Deadline: {o.deadline}"
            if o.trigger:
                details += f" | Trigger: {o.trigger}"

            claim = Claim.create(
                document_id=document_id,
                claim_text=f"Obligation: {details}",
                claim_type=ClaimType.OBLIGATION,
                evidence=ref,
                entity_id=o.id,
            )
            claims.append(claim)

        for d in understanding.dates:
            ref = EvidenceReference(
                document_id=document_id,
                page_start=d.page_number,
                page_end=d.page_number,
                source_span=d.source_span,
            )
            date_desc = f"{d.description} ({d.date_type}): {d.raw_text}"
            if d.normalized_date:
                date_desc += f" [ISO: {d.normalized_date}]"

            claim = Claim.create(
                document_id=document_id,
                claim_text=f"Date: {date_desc}",
                claim_type=ClaimType.DATE,
                evidence=ref,
                entity_id=d.id,
            )
            claims.append(claim)

        for f in understanding.review_flags:
            ref = EvidenceReference(
                document_id=document_id,
                page_start=f.page_start,
                page_end=f.page_end,
                source_span=f.source_span,
                clause_id=f.related_clause_id,
            )
            claim = Claim.create(
                document_id=document_id,
                claim_text=(
                    f"Review Flag ({f.severity.upper()}): {f.title} - {f.description}"
                ),
                claim_type=ClaimType.REVIEW_FLAG,
                evidence=ref,
                entity_id=f.id,
            )
            claims.append(claim)

        return claims
