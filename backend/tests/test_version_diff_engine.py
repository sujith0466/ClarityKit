"""Unit tests for VersionDiffEngine deterministic alignment (Phase 14)."""

import uuid

from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
)
from app.version_diff.diff_engine import VersionDiffEngine
from app.version_diff.models import (
    VersionDiffCategory,
    VersionDiffClassification,
)


def test_version_diff_engine_identical_documents() -> None:
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    understanding_1 = DocumentUnderstanding(
        document_id=doc1_id,
        parties=[
            ExtractedParty.create(
                document_id=doc1_id,
                name="Acme Corp",
                role="Client",
                page_number=1,
                source_span="Acme Corp",
            )
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc1_id,
                date_type="effective_date",
                raw_text="Jan 1, 2026",
                normalized_date="2026-01-01",
                description="Effective Date",
                page_number=1,
                source_span="Jan 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc1_id,
                obligor="Acme Corp",
                duty="pay fee",
                trigger=None,
                deadline="30 days",
                page_start=1,
                page_end=1,
                source_span="pay fee",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc1_id,
                clause_identifier="Section 1",
                title="Governing Law",
                category="general",
                text="State of NY",
                page_start=1,
                page_end=1,
                source_span="State of NY",
            )
        ],
    )

    understanding_2 = DocumentUnderstanding(
        document_id=doc2_id,
        parties=[
            ExtractedParty.create(
                document_id=doc2_id,
                name="Acme Corp",
                role="Client",
                page_number=1,
                source_span="Acme Corp",
            )
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc2_id,
                date_type="effective_date",
                raw_text="Jan 1, 2026",
                normalized_date="2026-01-01",
                description="Effective Date",
                page_number=1,
                source_span="Jan 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc2_id,
                obligor="Acme Corp",
                duty="pay fee",
                trigger=None,
                deadline="30 days",
                page_start=1,
                page_end=1,
                source_span="pay fee",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc2_id,
                clause_identifier="Section 1",
                title="Governing Law",
                category="general",
                text="State of NY",
                page_start=1,
                page_end=1,
                source_span="State of NY",
            )
        ],
    )

    findings = VersionDiffEngine.compute_diff(
        v1_doc_id=doc1_id,
        v1_doc_title="Doc_v1.pdf",
        v1_understanding=understanding_1,
        v2_doc_id=doc2_id,
        v2_doc_title="Doc_v2.pdf",
        v2_understanding=understanding_2,
    )

    assert len(findings) == 4
    for f in findings:
        assert f.classification == VersionDiffClassification.UNCHANGED


def test_version_diff_engine_add_remove_modify() -> None:
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    understanding_1 = DocumentUnderstanding(
        document_id=doc1_id,
        parties=[
            ExtractedParty.create(
                document_id=doc1_id,
                name="Alice Corp",
                role="Provider",
                page_number=1,
                source_span="Alice Corp",
            ),
            ExtractedParty.create(
                document_id=doc1_id,
                name="Old Guarantor",
                role="Guarantor",
                page_number=1,
                source_span="Old Guarantor",
            ),
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc1_id,
                date_type="effective_date",
                raw_text="Jan 1, 2026",
                normalized_date="2026-01-01",
                description="Effective Date",
                page_number=1,
                source_span="Jan 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc1_id,
                obligor="Alice Corp",
                duty="provide notice",
                trigger=None,
                deadline="30 days",
                page_start=2,
                page_end=2,
                source_span="provide notice 30 days",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc1_id,
                clause_identifier="Section 2",
                title="Arbitration",
                category="general",
                text="Arbitration in NY",
                page_start=2,
                page_end=2,
                source_span="Arbitration in NY",
            )
        ],
    )

    understanding_2 = DocumentUnderstanding(
        document_id=doc2_id,
        parties=[
            ExtractedParty.create(
                document_id=doc2_id,
                name="Alice Corp",
                role="Provider",
                page_number=1,
                source_span="Alice Corp",
            ),
            ExtractedParty.create(
                document_id=doc2_id,
                name="New Investor",
                role="Investor",
                page_number=1,
                source_span="New Investor",
            ),
        ],
        dates=[
            ExtractedDate.create(
                document_id=doc2_id,
                date_type="effective_date",
                raw_text="Feb 1, 2026",
                normalized_date="2026-02-01",
                description="Effective Date",
                page_number=1,
                source_span="Feb 1, 2026",
            )
        ],
        obligations=[
            ExtractedObligation.create(
                document_id=doc2_id,
                obligor="Alice Corp",
                duty="provide notice",
                trigger=None,
                deadline="60 days",
                page_start=2,
                page_end=2,
                source_span="provide notice 60 days",
            )
        ],
        clauses=[
            ExtractedClause.create(
                document_id=doc2_id,
                clause_identifier="Section 2",
                title="Arbitration",
                category="general",
                text="Arbitration in Delaware",
                page_start=2,
                page_end=2,
                source_span="Arbitration in Delaware",
            ),
            ExtractedClause.create(
                document_id=doc2_id,
                clause_identifier="Section 3",
                title="Data Privacy",
                category="general",
                text="GDPR compliance",
                page_start=3,
                page_end=3,
                source_span="GDPR compliance",
            ),
        ],
    )

    findings = VersionDiffEngine.compute_diff(
        v1_doc_id=doc1_id,
        v1_doc_title="Contract_Draft_1.pdf",
        v1_understanding=understanding_1,
        v2_doc_id=doc2_id,
        v2_doc_title="Contract_Draft_2.pdf",
        v2_understanding=understanding_2,
    )

    # 1. Parties: Alice Corp (UNCHANGED), Old Guarantor (REMOVED), New Investor (ADDED)
    alice_finding = next(f for f in findings if "Alice Corp" in f.title)
    assert alice_finding.classification == VersionDiffClassification.UNCHANGED

    guarantor_finding = next(f for f in findings if "Old Guarantor" in f.title)
    assert guarantor_finding.classification == VersionDiffClassification.REMOVED

    investor_finding = next(f for f in findings if "New Investor" in f.title)
    assert investor_finding.classification == VersionDiffClassification.ADDED

    # 2. Dates: Effective date modified (Jan 1 -> Feb 1)
    date_finding = next(f for f in findings if f.category == VersionDiffCategory.DATES)
    assert date_finding.classification == VersionDiffClassification.MODIFIED

    # 3. Obligations: Notice modified (30 days -> 60 days)
    ob_finding = next(
        f for f in findings if f.category == VersionDiffCategory.OBLIGATIONS
    )
    assert ob_finding.classification == VersionDiffClassification.MODIFIED

    # 4. Clauses: Arbitration modified, Data Privacy added
    arb_finding = next(f for f in findings if "Arbitration" in f.title)
    assert arb_finding.classification == VersionDiffClassification.MODIFIED

    dp_finding = next(f for f in findings if "Data Privacy" in f.title)
    assert dp_finding.classification == VersionDiffClassification.ADDED
