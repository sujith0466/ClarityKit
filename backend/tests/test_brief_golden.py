"""Golden benchmark evaluation tests for Lawyer-Preparation Brief generation."""

from typing import Any

import pytest

from app.auth.models import User
from app.brief.repository import InMemoryBriefRepository
from app.brief.service import BriefService
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.reasoning.gateway import ReasoningGateway

GOLDEN_SCENARIOS = [
    {
        "id": "scenario-lease",
        "title": "Commercial Lease Agreement",
        "parties": [("Acme Holdings LLC", "Landlord"), ("Beta Retail Inc", "Tenant")],
        "clauses": [
            (
                "Clause-1",
                "Premises and Term",
                "term",
                "5 year lease term commencing Jan 1 2026",
            ),
            (
                "Clause-2",
                "Rent Payment",
                "payment",
                "Tenant shall pay monthly base rent of $10,000",
            ),
            (
                "Clause-3",
                "Automatic Renewal",
                "renewal",
                "Agreement auto-renews unless notice given 90 days prior",
            ),
        ],
        "obligations": [
            ("Beta Retail Inc", "shall pay monthly base rent of $10,000", "monthly")
        ],
        "dates": [("effective_date", "2026-01-01", "2026-01-01")],
        "flags": [("renewal_lock_in", "Automatic Renewal Provision", "medium")],
    },
    {
        "id": "scenario-contractor",
        "title": "Independent Contractor Agreement",
        "parties": [("Nova Tech Inc", "Client"), ("John Doe Consulting", "Contractor")],
        "clauses": [
            (
                "Clause-1",
                "Services and IP Assignment",
                "intellectual_property",
                "All work product belongs to Client",
            ),
            (
                "Clause-2",
                "Indemnification",
                "indemnification",
                "Contractor shall indemnify Client for IP infringement",
            ),
        ],
        "obligations": [
            (
                "John Doe Consulting",
                "shall assign all right, title, and interest in work product",
                None,
            )
        ],
        "dates": [("effective_date", "2026-02-01", "2026-02-01")],
        "flags": [],
    },
    {
        "id": "scenario-msa",
        "title": "Master Services Agreement",
        "parties": [("Alpha Corp", "Provider"), ("Gamma LLC", "Customer")],
        "clauses": [
            (
                "Clause-1",
                "Limitation of Liability",
                "liability",
                "Total liability capped at fees paid in prior 12 months",
            ),
            (
                "Clause-2",
                "Termination for Convenience",
                "termination",
                "Either party may terminate on 30 days written notice",
            ),
        ],
        "obligations": [("Alpha Corp", "shall provide cloud hosting services", None)],
        "dates": [("effective_date", "2026-03-01", "2026-03-01")],
        "flags": [],
    },
    {
        "id": "scenario-nda",
        "title": "Mutual Non-Disclosure Agreement",
        "parties": [
            ("First Corp", "Disclosing Party"),
            ("Second Corp", "Receiving Party"),
        ],
        "clauses": [
            (
                "Clause-1",
                "Confidential Information",
                "confidentiality",
                "Parties shall hold proprietary info in strict confidence",
            ),
        ],
        "obligations": [
            (
                "Second Corp",
                "shall not disclose confidential information for 3 years",
                "3 years",
            )
        ],
        "dates": [("expiration_date", "2029-01-01", "2029-01-01")],
        "flags": [],
    },
    {
        "id": "scenario-employment",
        "title": "Executive Employment Agreement",
        "parties": [("Global Enterprise Inc", "Employer"), ("Jane Smith", "Executive")],
        "clauses": [
            (
                "Clause-1",
                "Restrictive Covenant",
                "non_compete",
                "Executive agrees not to compete for 12 months post termination",
            ),
        ],
        "obligations": [
            ("Jane Smith", "shall devote full business time and best efforts", None)
        ],
        "dates": [("effective_date", "2026-04-01", "2026-04-01")],
        "flags": [("restrictive_covenant", "Non-Compete Covenant", "medium")],
    },
    {
        "id": "scenario-software",
        "title": "Software License Agreement",
        "parties": [("SoftCo LLC", "Licensor"), ("Enterprise Corp", "Licensee")],
        "clauses": [
            (
                "Clause-1",
                "Grant of License",
                "general",
                "Non-exclusive, non-transferable license granted",
            ),
            (
                "Clause-2",
                "Dispute Resolution",
                "dispute_resolution",
                "Disputes resolved via binding arbitration in New York",
            ),
        ],
        "obligations": [
            ("Enterprise Corp", "shall not reverse engineer the software", None)
        ],
        "dates": [("effective_date", "2026-05-01", "2026-05-01")],
        "flags": [],
    },
    {
        "id": "scenario-jv",
        "title": "Joint Venture Operating Agreement",
        "parties": [("Ventures One LLC", "Member A"), ("Ventures Two LLC", "Member B")],
        "clauses": [
            (
                "Clause-1",
                "Capital Contributions",
                "payment",
                "Initial contribution of $500,000 per member",
            ),
            (
                "Clause-2",
                "Unilateral Rights",
                "general",
                "Managing member holds sole discretion over budget",
            ),
        ],
        "obligations": [
            ("Ventures One LLC", "shall contribute $500,000 within 10 days", "10 days")
        ],
        "dates": [("effective_date", "2026-06-01", "2026-06-01")],
        "flags": [("unilateral_discretion", "Unilateral Budget Discretion", "low")],
    },
    {
        "id": "scenario-billofsale",
        "title": "As-Is Bill of Sale",
        "parties": [("Seller Bob", "Seller"), ("Buyer Alice", "Buyer")],
        "clauses": [
            (
                "Clause-1",
                "As-Is Condition",
                "general",
                "Goods sold as-is with all faults and no express warranties",
            ),
        ],
        "obligations": [
            ("Buyer Alice", "shall accept delivery at current location", None)
        ],
        "dates": [("effective_date", "2026-07-01", "2026-07-01")],
        "flags": [("ambiguous_term", "As-Is Standard", "low")],
    },
]


@pytest.mark.parametrize("scenario", GOLDEN_SCENARIOS)
def test_golden_scenario_brief_generation(scenario: dict[str, Any]) -> None:
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    brief_repo = InMemoryBriefRepository(document_repository=doc_repo)
    user = User(
        user_id="gold-user",
        email="gold@example.com",
        password_hash="dummy",
        name="Gold User",
    )

    doc = Document(
        document_id=scenario["id"],
        user_id=user.user_id,
        filename=f"{scenario['title']}.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="test_storage",
        content_hash="sha-gold",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page_text = f"{scenario['title']}. " + " ".join([c[3] for c in scenario["clauses"]])
    page = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text=page_text,
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page])

    extracted_parties = [
        ExtractedParty.create(
            document_id=doc.id, name=p[0], role=p[1], page_number=1, source_span=p[0]
        )
        for p in scenario["parties"]
    ]
    extracted_clauses = [
        ExtractedClause.create(
            document_id=doc.id,
            clause_identifier=c[0],
            title=c[1],
            category=c[2],
            text=c[3],
            page_start=1,
            page_end=1,
            source_span=c[3][:50],
        )
        for c in scenario["clauses"]
    ]
    extracted_obligations = [
        ExtractedObligation.create(
            document_id=doc.id,
            obligor=o[0],
            duty=o[1],
            trigger=None,
            deadline=o[2],
            page_start=1,
            page_end=1,
            source_span=o[1],
        )
        for o in scenario["obligations"]
    ]
    extracted_dates = [
        ExtractedDate.create(
            document_id=doc.id,
            date_type=d[0],
            raw_text=d[1],
            normalized_date=d[2],
            description=d[0],
            page_number=1,
            source_span=d[1],
        )
        for d in scenario["dates"]
    ]
    extracted_flags = [
        ExtractedReviewFlag.create(
            document_id=doc.id,
            flag_type=f[0],
            title=f[1],
            description=f[1],
            severity=f[2],
            page_start=1,
            page_end=1,
            source_span=f[1],
        )
        for f in scenario["flags"]
    ]

    extraction_repo.save_understanding(
        document_id=doc.id,
        parties=extracted_parties,
        clauses=extracted_clauses,
        obligations=extracted_obligations,
        dates=extracted_dates,
        review_flags=extracted_flags,
    )

    service = BriefService(
        brief_repository=brief_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        reasoning_gateway=ReasoningGateway(),
    )

    brief = service.generate_brief(doc.id, user.user_id)

    assert brief is not None
    assert brief.document_id == scenario["id"]
    assert len(brief.questions_for_lawyer) > 0
    assert len(brief.documents_to_bring) > 0
    assert len(brief.facts_to_confirm) > 0
    assert brief.completeness_score > 0.4
    assert "IMPORTANT NOTICE" in brief.disclaimer

    # Export PDF verify
    pdf_bytes = service.export_brief_pdf(brief.id, user.user_id)
    assert len(pdf_bytes) > 200
    assert pdf_bytes.startswith(b"%PDF-1.4")
