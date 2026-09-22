"""Service layer orchestrating Document Version Diff analysis (Phase 14)."""

import logging
import uuid
from datetime import UTC, datetime

from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.evidence.models import (
    Claim,
    ClaimType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.evidence.validators import EvidenceValidator
from app.extraction.models import DocumentUnderstanding
from app.extraction.repository import (
    ExtractionRepository,
    get_extraction_repository,
)
from app.processing.repository import PageRepository, in_memory_page_repository
from app.trust.models import SafetyStatus, TrustTier
from app.version_diff.diff_engine import VersionDiffEngine
from app.version_diff.models import (
    DocumentVersionDiff,
    VersionDiffClassification,
    VersionDiffFinding,
    VersionDiffNotFoundError,
    VersionDiffSummary,
    VersionDocumentRef,
    VersionEvidenceRef,
)
from app.version_diff.repository import (
    VersionDiffRepository,
    in_memory_version_diff_repository,
)
from app.version_diff.validation import VersionDiffValidator

logger = logging.getLogger(__name__)


class VersionDiffService:
    """Coordinates version pair validation, deterministic diff, Phase 7 evidence
    validation, and persistence.
    """

    def __init__(
        self,
        version_diff_repository: VersionDiffRepository | None = None,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
    ) -> None:
        self._diff_repo = version_diff_repository or in_memory_version_diff_repository
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or get_extraction_repository()
        self._validator = VersionDiffValidator(document_repository=self._doc_repo)

    def generate_version_diff(
        self,
        v1_document_id: str,
        v2_document_id: str,
        user_id: str,
        title: str | None = None,
    ) -> DocumentVersionDiff:
        """Generate, validate, and persist a version diff between
        Version 1 and Version 2.
        """
        # 1. Validate boundary & ownership
        v1_doc, v2_doc = self._validator.validate_version_pair(
            v1_document_id=v1_document_id,
            v2_document_id=v2_document_id,
            user_id=user_id,
        )

        # 2. Load page texts for mechanical evidence resolution
        v1_page_texts = self._load_page_texts(v1_doc.id)
        v2_page_texts = self._load_page_texts(v2_doc.id)

        # 3. Load Phase 6 structured extractions
        v1_understanding = self._load_understanding(v1_doc.id, user_id)
        v2_understanding = self._load_understanding(v2_doc.id, user_id)

        # 4. Enforce version compatibility (reject unrelated documents)
        self._validator.validate_version_compatibility(
            v1_doc=v1_doc,
            v2_doc=v2_doc,
            v1_understanding=v1_understanding,
            v2_understanding=v2_understanding,
        )

        # 5. Deterministic diff execution
        raw_findings = VersionDiffEngine.compute_diff(
            v1_doc_id=v1_doc.id,
            v1_doc_title=v1_doc.filename,
            v1_understanding=v1_understanding,
            v2_doc_id=v2_doc.id,
            v2_doc_title=v2_doc.filename,
            v2_understanding=v2_understanding,
        )

        # 6. Authoritative Phase 7 Evidence Validation & Trust/Safety Integration
        validated_findings: list[VersionDiffFinding] = []
        for finding in raw_findings:
            v1_valid = self._validate_evidence_list(
                finding.v1_evidence, v1_page_texts, v1_doc.id
            )
            v2_valid = self._validate_evidence_list(
                finding.v2_evidence, v2_page_texts, v2_doc.id
            )

            all_evidence_valid = v1_valid and v2_valid

            # Enforce NO EVIDENCE -> NO DOCUMENT-SPECIFIC CLAIM
            if not all_evidence_valid:
                finding.classification = VersionDiffClassification.UNRESOLVED
                finding.trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                finding.safety_status = SafetyStatus.REVIEW_REQUIRED
                finding.description += (
                    " [Notice: One or more evidence citations could not be "
                    "mechanically verified against the source text.]"
                )
            else:
                if finding.classification in (
                    VersionDiffClassification.UNCHANGED,
                    VersionDiffClassification.ADDED,
                    VersionDiffClassification.REMOVED,
                    VersionDiffClassification.MODIFIED,
                ):
                    finding.trust_tier = TrustTier.DOCUMENT_FACT
                    finding.safety_status = SafetyStatus.SAFE
                elif (
                    finding.classification == VersionDiffClassification.POTENTIAL_CHANGE
                ):
                    finding.trust_tier = TrustTier.DOCUMENT_FACT
                    finding.safety_status = SafetyStatus.REVIEW_REQUIRED
                else:
                    finding.trust_tier = TrustTier.PROFESSIONAL_REVIEW_NEEDED
                    finding.safety_status = SafetyStatus.LIMITED

            validated_findings.append(finding)

        # 6. Compute summary
        summary = VersionDiffSummary.from_findings(validated_findings)

        # 7. Construct DocumentVersionDiff
        diff_id = str(uuid.uuid4())
        diff_title = (
            title.strip()
            if title and title.strip()
            else f"Diff: {v1_doc.filename} vs {v2_doc.filename}"
        )
        now_str = datetime.now(UTC).isoformat()

        version_diff = DocumentVersionDiff(
            id=diff_id,
            user_id=user_id,
            title=diff_title,
            v1_document=VersionDocumentRef(
                id=v1_doc.id, filename=v1_doc.filename, version_label="Version 1 (Base)"
            ),
            v2_document=VersionDocumentRef(
                id=v2_doc.id,
                filename=v2_doc.filename,
                version_label="Version 2 (Revised)",
            ),
            findings=validated_findings,
            summary=summary,
            created_at=now_str,
            updated_at=now_str,
        )

        return self._diff_repo.save_version_diff(version_diff, user_id)

    def get_version_diff_by_id(self, diff_id: str, user_id: str) -> DocumentVersionDiff:
        """Retrieve a specific version diff by ID for an authorized user."""
        diff = self._diff_repo.get_version_diff_by_id(diff_id, user_id)
        if diff is None:
            raise VersionDiffNotFoundError(
                f"Version diff '{diff_id}' not found or unauthorized."
            )
        return diff

    def list_version_diffs_for_user(self, user_id: str) -> list[DocumentVersionDiff]:
        """List all version diffs belonging to the authenticated user."""
        return self._diff_repo.list_version_diffs_for_user(user_id)

    def delete_version_diff(self, diff_id: str, user_id: str) -> bool:
        """Delete a version diff record."""
        return self._diff_repo.delete_version_diff(diff_id, user_id)

    def delete_diffs_for_document(self, document_id: str, user_id: str) -> int:
        """Cascade delete all version diffs containing the specified document ID."""
        return self._diff_repo.delete_diffs_for_document(document_id, user_id)

    def _load_page_texts(self, document_id: str) -> dict[int, str]:
        pages = self._page_repo.get_pages_by_document(document_id)
        return {p.page_number: p.text for p in pages}

    def _load_understanding(
        self, document_id: str, user_id: str
    ) -> DocumentUnderstanding:
        understanding = self._extraction_repo.get_understanding_by_document(
            document_id, user_id
        )
        if understanding is None:
            return DocumentUnderstanding(document_id=document_id)
        return understanding

    @staticmethod
    def _validate_evidence_list(
        evidence_list: list[VersionEvidenceRef],
        page_texts: dict[int, str],
        document_id: str,
    ) -> bool:
        """Route citations through authoritative Phase 7 EvidenceValidator."""
        all_valid = True
        for ref in evidence_list:
            if not ref.source_span or not page_texts:
                ref.validation_status = EvidenceValidationStatus.INVALID
                all_valid = False
                continue

            claim_ref = EvidenceReference(
                document_id=document_id,
                page_start=ref.page_start,
                page_end=ref.page_end,
                source_span=ref.source_span,
                section=ref.section,
            )
            claim = Claim.create(
                document_id=document_id,
                claim_text=ref.exact_quote or ref.source_span,
                claim_type=ClaimType.CLAUSE,
                evidence=claim_ref,
            )

            # Invoke authoritative Phase 7 EvidenceValidator
            validated_claim = EvidenceValidator.validate_claim(claim, page_texts)

            if validated_claim.evidence:
                ref.validation_status = validated_claim.evidence.validation_status
                ref.char_start = validated_claim.evidence.char_start
                ref.char_end = validated_claim.evidence.char_end
                if validated_claim.evidence.source_text:
                    ref.exact_quote = validated_claim.evidence.source_text

            if ref.validation_status != EvidenceValidationStatus.VALID:
                all_valid = False

        return all_valid
