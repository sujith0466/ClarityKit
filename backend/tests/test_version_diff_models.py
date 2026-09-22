"""Unit tests for Version Diff domain models and serialization (Phase 14)."""

import uuid

from app.evidence.models import EvidenceValidationStatus
from app.trust.models import SafetyStatus, TrustTier
from app.version_diff.models import (
    DocumentVersionDiff,
    VersionDiffCategory,
    VersionDiffClassification,
    VersionDiffFinding,
    VersionDiffSummary,
    VersionDocumentRef,
    VersionEvidenceRef,
)


def test_version_evidence_ref_serialization() -> None:
    doc_id = str(uuid.uuid4())
    ref = VersionEvidenceRef(
        document_id=doc_id,
        version_label="v1",
        document_title="Employment_Agreement_v1.pdf",
        page_start=1,
        page_end=2,
        source_span="Termination notice of 30 days.",
        exact_quote="Termination notice of 30 days.",
        section="Section 8",
        validation_status=EvidenceValidationStatus.VALID,
        char_start=100,
        char_end=130,
        trust_tier=TrustTier.DOCUMENT_FACT,
    )

    data = ref.to_dict()
    assert data["document_id"] == doc_id
    assert data["version_label"] == "v1"
    assert data["validation_status"] == "VALID"
    assert data["char_start"] == 100

    deserialized = VersionEvidenceRef.from_dict(data)
    assert deserialized.document_id == doc_id
    assert deserialized.version_label == "v1"
    assert deserialized.validation_status == EvidenceValidationStatus.VALID


def test_version_diff_finding_serialization() -> None:
    finding_id = str(uuid.uuid4())
    v1_ref = VersionEvidenceRef(
        document_id=str(uuid.uuid4()),
        version_label="v1",
        document_title="Draft_1.pdf",
        page_start=3,
        page_end=3,
        source_span="30 days",
        exact_quote="30 days notice",
        section="Termination",
        validation_status=EvidenceValidationStatus.VALID,
    )
    v2_ref = VersionEvidenceRef(
        document_id=str(uuid.uuid4()),
        version_label="v2",
        document_title="Draft_2.pdf",
        page_start=3,
        page_end=3,
        source_span="60 days",
        exact_quote="60 days notice",
        section="Termination",
        validation_status=EvidenceValidationStatus.VALID,
    )

    finding = VersionDiffFinding(
        id=finding_id,
        category=VersionDiffCategory.NOTICE,
        title="Notice Period Modified: 30 Days to 60 Days",
        description=(
            "Version 2 specifies 60 days notice, whereas Version 1 specified 30 days."
        ),
        classification=VersionDiffClassification.MODIFIED,
        v1_evidence=[v1_ref],
        v2_evidence=[v2_ref],
        lawyer_questions=["Is the extension to 60 days acceptable?"],
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
    )

    data = finding.to_dict()
    assert data["id"] == finding_id
    assert data["classification"] == "MODIFIED"
    assert len(data["v1_evidence"]) == 1
    assert len(data["v2_evidence"]) == 1

    deserialized = VersionDiffFinding.from_dict(data)
    assert deserialized.id == finding_id
    assert deserialized.classification == VersionDiffClassification.MODIFIED
    assert len(deserialized.v1_evidence) == 1
    assert len(deserialized.v2_evidence) == 1


def test_document_version_diff_full_roundtrip() -> None:
    diff_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    v1_id = str(uuid.uuid4())
    v2_id = str(uuid.uuid4())

    v1_doc = VersionDocumentRef(
        id=v1_id, filename="MSA_v1.pdf", version_label="Version 1 (Base)"
    )
    v2_doc = VersionDocumentRef(
        id=v2_id, filename="MSA_v2.pdf", version_label="Version 2 (Revised)"
    )

    finding = VersionDiffFinding(
        id=str(uuid.uuid4()),
        category=VersionDiffCategory.CLAUSE,
        title="Clause Added: Security Schedule",
        description="Version 2 includes a Security Schedule not present in Version 1.",
        classification=VersionDiffClassification.ADDED,
        v1_evidence=[],
        v2_evidence=[
            VersionEvidenceRef(
                document_id=v2_id,
                version_label="v2",
                document_title="MSA_v2.pdf",
                page_start=5,
                page_end=5,
                source_span="Security Schedule",
                validation_status=EvidenceValidationStatus.VALID,
            )
        ],
        trust_tier=TrustTier.DOCUMENT_FACT,
        safety_status=SafetyStatus.SAFE,
    )

    summary = VersionDiffSummary.from_findings([finding])
    assert summary.total_findings == 1
    assert summary.added_count == 1

    diff = DocumentVersionDiff(
        id=diff_id,
        user_id=user_id,
        title="MSA Version Comparison",
        v1_document=v1_doc,
        v2_document=v2_doc,
        findings=[finding],
        summary=summary,
    )

    data = diff.to_dict()
    deserialized = DocumentVersionDiff.from_dict(data)

    assert deserialized.id == diff_id
    assert deserialized.user_id == user_id
    assert deserialized.v1_document.id == v1_id
    assert deserialized.v2_document.id == v2_id
    assert len(deserialized.findings) == 1
    assert deserialized.summary.added_count == 1
