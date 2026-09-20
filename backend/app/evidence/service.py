import logging
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import (
    DocumentRepository,
    in_memory_document_repository,
)
from app.evidence.models import (
    Claim,
    ClaimType,
    DocumentEvidenceReport,
    DocumentNotFoundError,
    DocumentNotReadyForEvidenceError,
    EvidenceReference,
    InvalidEvidenceInputError,
)
from app.evidence.repository import (
    EvidenceRepository,
    get_evidence_repository,
)
from app.evidence.validators import EvidenceValidator
from app.extraction.models import (
    DocumentUnderstanding,
)
from app.extraction.repository import (
    ExtractionRepository,
    get_extraction_repository,
)
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)

logger = logging.getLogger(__name__)


class EvidenceService:
    """Coordinates mechanical evidence verification and coverage calculation."""

    MAX_AD_HOC_CLAIMS = 50
    MAX_CLAIM_TEXT_LEN = 2000
    MAX_SOURCE_SPAN_LEN = 5000

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
        evidence_repository: EvidenceRepository | None = None,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or get_extraction_repository()
        self._evidence_repo = evidence_repository or get_evidence_repository()

    def _get_authorized_page_texts(
        self, document_id: str, user_id: str
    ) -> dict[int, str]:
        """Validate document ownership and return authoritative page texts."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError(f"Document {document_id} not found.")

        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForEvidenceError(
                f"Document status is '{doc.status.value}'. "
                "Evidence requires 'ready' status."
            )

        pages = self._page_repo.get_pages_by_document(document_id)
        if not pages:
            raise DocumentNotReadyForEvidenceError(
                f"No processed pages found for document {document_id}."
            )

        return {p.page_number: p.text for p in pages}

    def generate_document_evidence(
        self, document_id: str, user_id: str
    ) -> DocumentEvidenceReport:
        """Generate, validate, and persist mechanical evidence report."""
        page_texts = self._get_authorized_page_texts(document_id, user_id)

        understanding = self._extraction_repo.get_understanding_by_document(
            document_id, user_id
        )
        if understanding is None:
            understanding = DocumentUnderstanding(document_id=document_id)

        claims = EvidenceValidator.claims_from_understanding(document_id, understanding)

        validated_claims, coverage = EvidenceValidator.validate_claims(
            claims, page_texts
        )

        report = DocumentEvidenceReport(
            document_id=document_id,
            claims=validated_claims,
            coverage=coverage,
        )

        self._evidence_repo.save_evidence_report(report)
        return report

    def get_document_evidence(
        self, document_id: str, user_id: str
    ) -> DocumentEvidenceReport:
        """Retrieve persisted evidence report or generate on demand."""
        page_texts = self._get_authorized_page_texts(document_id, user_id)

        report = self._evidence_repo.get_evidence_report(document_id, user_id)
        if report is not None:
            validated_claims, coverage = EvidenceValidator.validate_claims(
                report.claims, page_texts
            )
            report.claims = validated_claims
            report.coverage = coverage
            return report

        return self.generate_document_evidence(document_id, user_id)

    def validate_ad_hoc_claims(
        self,
        document_id: str,
        user_id: str,
        raw_claims: list[dict[str, Any]],
    ) -> DocumentEvidenceReport:
        """Validate ad-hoc claim payloads against authoritative page texts."""
        if not isinstance(raw_claims, list):
            raise InvalidEvidenceInputError("Claims payload must be a list.")

        if len(raw_claims) > self.MAX_AD_HOC_CLAIMS:
            raise InvalidEvidenceInputError(
                f"Maximum of {self.MAX_AD_HOC_CLAIMS} claims can be validated at once."
            )

        page_texts = self._get_authorized_page_texts(document_id, user_id)

        claims: list[Claim] = []
        for item in raw_claims:
            if not isinstance(item, dict):
                continue

            claim_text = str(item.get("claim_text", "")).strip()
            if not claim_text:
                continue

            if len(claim_text) > self.MAX_CLAIM_TEXT_LEN:
                claim_text = claim_text[: self.MAX_CLAIM_TEXT_LEN]

            claim_type_str = str(item.get("claim_type", "general_fact")).lower()
            claim_type = (
                ClaimType(claim_type_str)
                if claim_type_str in [c.value for c in ClaimType]
                else ClaimType.GENERAL_FACT
            )

            raw_ref = item.get("evidence")
            evidence_ref: EvidenceReference | None = None

            if isinstance(raw_ref, dict):
                page_start = int(raw_ref.get("page_start", 1))
                page_end = int(raw_ref.get("page_end", page_start))
                source_span = str(raw_ref.get("source_span", "")).strip()

                if len(source_span) > self.MAX_SOURCE_SPAN_LEN:
                    source_span = source_span[: self.MAX_SOURCE_SPAN_LEN]

                evidence_ref = EvidenceReference(
                    document_id=document_id,
                    page_start=page_start,
                    page_end=page_end,
                    source_span=source_span,
                    section=raw_ref.get("section"),
                    clause_id=raw_ref.get("clause_id"),
                )

            claim = Claim.create(
                document_id=document_id,
                claim_text=claim_text,
                claim_type=claim_type,
                evidence=evidence_ref,
                entity_id=item.get("entity_id"),
            )
            claims.append(claim)

        validated_claims, coverage = EvidenceValidator.validate_claims(
            claims, page_texts
        )

        return DocumentEvidenceReport(
            document_id=document_id,
            claims=validated_claims,
            coverage=coverage,
        )
