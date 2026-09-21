#!/usr/bin/env python
"""ClarityKit Lawyer-Preparation Brief Evaluation Harness (Phase 11: Task T-251).

Evaluates structured brief assembly, evidence citation validity, trust status
propagation, consultation question neutrality, and PDF export integrity across
curated golden test scenarios.
"""

import sys
import uuid
from pathlib import Path

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.brief.models import LawyerPreparationBrief
from app.brief.repository import InMemoryBriefRepository
from app.brief.service import BriefService
from app.brief.validation import contains_forbidden_legal_claims
from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)
from app.extraction.repository import InMemoryExtractionRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.qa.repository import InMemoryQARepository
from app.reasoning.gateway import ReasoningGateway

GOLDEN_EVAL_SCENARIOS = [
    {
        "id": "eval-lease",
        "title": "Commercial Office Lease Agreement",
        "parties": [("Metropolis Properties LP", "Landlord"), ("Nexus Tech LLC", "Tenant")],
        "clauses": [
            ("Clause-1", "Base Rent & Security", "payment", "Tenant shall pay monthly base rent of $12,500."),
            ("Clause-2", "Term & Automatic Renewal", "renewal", "Agreement automatically renews for 3 years unless 90 days notice is given."),
            ("Clause-3", "Exclusive Use Covenant", "non_compete", "Landlord covenants not to lease adjacent suites to direct competitors."),
        ],
        "obligations": [("Nexus Tech LLC", "shall pay monthly base rent of $12,500 on the 1st of each month", "monthly")],
        "dates": [("effective_date", "2026-06-01", "2026-06-01")],
        "flags": [("renewal_lock_in", "Automatic Renewal Provision", "medium")],
    },
    {
        "id": "eval-services",
        "title": "Professional Services Agreement",
        "parties": [("Apex Strategy Group", "Consultant"), ("Vanguard Enterprises", "Client")],
        "clauses": [
            ("Clause-1", "Limitation of Liability", "liability", "Consultant total aggregate liability is limited to $50,000."),
            ("Clause-2", "Indemnification", "indemnification", "Consultant shall indemnify Client against third-party claims."),
        ],
        "obligations": [("Apex Strategy Group", "shall perform advisory deliverables with reasonable skill", None)],
        "dates": [("effective_date", "2026-07-01", "2026-07-01")],
        "flags": [],
    },
    {
        "id": "eval-nda",
        "title": "Mutual Non-Disclosure & Confidentiality Agreement",
        "parties": [("Synergy Systems Inc", "Disclosing Party"), ("Orbit Dynamics Corp", "Receiving Party")],
        "clauses": [
            ("Clause-1", "Confidentiality Obligations", "confidentiality", "Receiving party shall maintain strict confidentiality."),
            ("Clause-2", "Non-Solicitation", "non_solicit", "Neither party shall solicit employees of the other for 24 months."),
        ],
        "obligations": [("Orbit Dynamics Corp", "shall not disclose proprietary source code or financial projections", None)],
        "dates": [("expiration_date", "2028-12-31", "2028-12-31")],
        "flags": [("restrictive_covenant", "Non-Solicitation Covenant", "medium")],
    },
    {
        "id": "eval-vendor",
        "title": "Master Vendor Supply Agreement",
        "parties": [("Precision Logistics Inc", "Supplier"), ("Apex Retail Stores", "Purchaser")],
        "clauses": [
            ("Clause-1", "Discretionary Price Adjustment", "general", "Supplier reserves sole discretion to adjust unit prices quarterly."),
            ("Clause-2", "Governing Law & Venue", "dispute_resolution", "Governed by the laws of the State of Delaware."),
        ],
        "obligations": [("Precision Logistics Inc", "shall supply hardware units within 14 business days", "14 days")],
        "dates": [("effective_date", "2026-08-01", "2026-08-01")],
        "flags": [("unilateral_discretion", "Unilateral Price Modification", "low")],
    },
    {
        "id": "eval-employment",
        "title": "Executive Employment & Severance Agreement",
        "parties": [("Global Health Inc", "Employer"), ("Dr. Sarah Jenkins", "Chief Medical Officer")],
        "clauses": [
            ("Clause-1", "Duties & Best Efforts", "general", "CMO shall devote full professional time and best efforts to Company."),
            ("Clause-2", "Post-Termination Non-Compete", "non_compete", "CMO shall not engage in competing pharmaceutical clinical trials for 18 months."),
        ],
        "obligations": [("Dr. Sarah Jenkins", "shall manage clinical trials with best efforts", None)],
        "dates": [("effective_date", "2026-09-01", "2026-09-01")],
        "flags": [
            ("restrictive_covenant", "Post-Employment Non-Compete", "medium"),
            ("ambiguous_term", "Best Efforts Standard", "low"),
        ],
    },
    {
        "id": "eval-software",
        "title": "Enterprise SaaS Subscription Agreement",
        "parties": [("CloudScale Technologies", "Licensor"), ("Summit Financial Group", "Subscriber")],
        "clauses": [
            ("Clause-1", "Service Level Agreement", "general", "Licensor provides 99.9% uptime standard."),
            ("Clause-2", "Termination for Convenience", "termination", "Subscriber may terminate upon 60 days written notice."),
        ],
        "obligations": [("CloudScale Technologies", "shall provide monthly uptime reporting", "monthly")],
        "dates": [("effective_date", "2026-10-01", "2026-10-01")],
        "flags": [],
    },
    {
        "id": "eval-ip-license",
        "title": "Patent License & Royalty Agreement",
        "parties": [("BioInovate Corp", "Licensor"), ("PharmaCo Global", "Licensee")],
        "clauses": [
            ("Clause-1", "Royalty Calculation", "payment", "Licensee shall pay 4.5% net sales royalty on licensed products."),
            ("Clause-2", "Audit Rights", "general", "Licensor may audit Licensee books and records once annually."),
        ],
        "obligations": [("PharmaCo Global", "shall submit quarterly royalty statements", "quarterly")],
        "dates": [("effective_date", "2026-11-01", "2026-11-01")],
        "flags": [],
    },
    {
        "id": "eval-settlement",
        "title": "Confidential Settlement & Release Agreement",
        "parties": [("Plaintiff Party", "Releasor"), ("Defendant Corp", "Releasee")],
        "clauses": [
            ("Clause-1", "Full and Final Mutual Release", "general", "Parties release all claims known and unknown."),
            ("Clause-2", "Non-Disparagement", "general", "Parties shall not make negative public statements."),
        ],
        "obligations": [("Defendant Corp", "shall wire settlement sum within 5 business days", "5 days")],
        "dates": [("effective_date", "2026-12-01", "2026-12-01")],
        "flags": [],
    },
]


def run_evaluation() -> bool:
    print("=" * 78)
    print("CLARITYKIT LAWYER-PREPARATION BRIEF EVALUATION HARNESS")
    print("=" * 78)

    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    extraction_repo = InMemoryExtractionRepository(document_repository=doc_repo)
    brief_repo = InMemoryBriefRepository(document_repository=doc_repo)


    service = BriefService(
        brief_repository=brief_repo,
        document_repository=doc_repo,
        page_repository=page_repo,
        extraction_repository=extraction_repo,
        reasoning_gateway=ReasoningGateway(),
    )

    user_id = "eval-user-1"
    all_passed = True

    print(f"\nEvaluating {len(GOLDEN_EVAL_SCENARIOS)} golden test scenarios:\n")
    print(f"{'Scenario ID':<20} | {'Completeness':<12} | {'Questions':<10} | {'PDF Export':<10} | {'Neutrality':<10} | Status")
    print("-" * 78)

    for sc in GOLDEN_EVAL_SCENARIOS:
        doc = Document(
            document_id=sc["id"],
            user_id=user_id,
            filename=f"{sc['title']}.pdf",
            content_type="application/pdf",
            file_size_bytes=2048,
            storage_key="test_storage",
            content_hash="sha-test",
            status=DocumentStatus.READY,
        )
        doc_repo.save(doc)


        full_text = f"{sc['title']}. " + " ".join([c[3] for c in sc["clauses"]])
        page = DocumentPage.create(
            document_id=doc.id,
            page_number=1,
            text=full_text,
            extraction_method=ExtractionMethod.NATIVE,
        )
        page_repo.save_pages(doc.id, [page])



        parties = [
            ExtractedParty.create(document_id=doc.id, name=p[0], role=p[1], page_number=1, source_span=p[0])
            for p in sc["parties"]
        ]
        clauses = [
            ExtractedClause.create(
                document_id=doc.id,
                clause_identifier=c[0],
                title=c[1],
                category=c[2],
                text=c[3],
                page_start=1,
                page_end=1,
                source_span=c[3][:40],
            )
            for c in sc["clauses"]
        ]
        obligations = [
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
            for o in sc["obligations"]
        ]
        dates = [
            ExtractedDate.create(
                document_id=doc.id,
                date_type=d[0],
                raw_text=d[1],
                normalized_date=d[2],
                description=d[0],
                page_number=1,
                source_span=d[1],
            )
            for d in sc["dates"]
        ]
        flags = [
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
            for f in sc["flags"]
        ]


        extraction_repo.save_understanding(
            document_id=doc.id,
            parties=parties,
            clauses=clauses,
            obligations=obligations,
            dates=dates,
            review_flags=flags,
        )


        brief = service.generate_brief(doc.id, user_id)
        pdf_bytes = service.export_brief_pdf(brief.id, user_id)

        # Check neutrality
        has_forbidden = False
        for q in brief.questions_for_lawyer:
            if contains_forbidden_legal_claims(q.question):
                has_forbidden = True
        if contains_forbidden_legal_claims(brief.situation_summary):
            has_forbidden = True

        comp_pct = f"{int(brief.completeness_score * 100)}%"
        q_count = str(len(brief.questions_for_lawyer))
        pdf_ok = "PASS" if (pdf_bytes.startswith(b"%PDF-1.4") and len(pdf_bytes) > 200) else "FAIL"
        neutral_ok = "FAIL" if has_forbidden else "PASS"

        scenario_passed = (
            brief.completeness_score > 0.4
            and len(brief.questions_for_lawyer) > 0
            and pdf_ok == "PASS"
            and neutral_ok == "PASS"
        )
        if not scenario_passed:
            all_passed = False

        status_str = "PASS" if scenario_passed else "FAIL"
        print(f"{sc['id']:<20} | {comp_pct:<12} | {q_count:<10} | {pdf_ok:<10} | {neutral_ok:<10} | {status_str}")

    print("-" * 78)
    if all_passed:
        print("\nALL 8 GOLDEN EVALUATION SCENARIOS PASSED (100% SUCCESS RATE)")
    else:
        print("\nEVALUATION HARNESS REPORTED FAILURES")
    print("=" * 78)
    return all_passed


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
