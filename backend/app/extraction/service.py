import logging
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import (
    DocumentRepository,
    in_memory_document_repository,
)
from app.extraction.models import (
    DocumentNotFoundError,
    DocumentNotReadyForExtractionError,
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)
from app.extraction.repository import (
    ExtractionRepository,
    get_extraction_repository,
)
from app.extraction.validators import ExtractionValidator
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)
from app.reasoning.gateway import (
    ReasoningGateway,
    get_reasoning_gateway,
)
from app.reasoning.models import ReasoningRequest

logger = logging.getLogger(__name__)


class ExtractionService:
    """Coordinates structured legal extraction from processed document pages."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        extraction_repository: ExtractionRepository | None = None,
        reasoning_gateway: ReasoningGateway | None = None,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._extraction_repo = extraction_repository or get_extraction_repository()
        self._reasoning_gateway = reasoning_gateway or get_reasoning_gateway()

    def extract_document(
        self,
        document_id: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentUnderstanding:
        """Execute structured extraction for a document and persist results."""
        # 1. Tenant ownership validation
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError(f"Document {document_id} not found.")

        # 2. Check document status is READY
        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyForExtractionError(
                f"Document status is '{doc.status.value}'. "
                "Extraction requires 'ready' status."
            )

        # 3. Retrieve processed pages
        pages = self._page_repo.get_pages_by_document(document_id)
        if not pages:
            raise DocumentNotReadyForExtractionError(
                f"No processed pages found for document {document_id}."
            )

        pages_payload = [
            {
                "id": p.id,
                "page_number": p.page_number,
                "text": p.text,
                "char_count": p.char_count,
            }
            for p in pages
        ]

        # 4. Invoke Reasoning Gateway
        reasoning_req = ReasoningRequest(
            document_id=document_id,
            pages=pages_payload,
            metadata=metadata or {},
        )
        raw_result = self._reasoning_gateway.extract_structured_data(reasoning_req)

        # 5. Transform raw entities to domain entities
        # A. Parties
        parties: list[ExtractedParty] = [
            ExtractedParty.create(
                document_id=document_id,
                name=raw_p.name,
                role=raw_p.role,
                page_number=raw_p.page_number,
                source_span=raw_p.source_span,
            )
            for raw_p in raw_result.parties
        ]

        # B. Clauses
        clauses: list[ExtractedClause] = []
        clause_id_map: dict[str, str] = {}  # identifier -> clause.id
        for raw_c in raw_result.clauses:
            clause = ExtractedClause.create(
                document_id=document_id,
                clause_identifier=raw_c.clause_identifier,
                title=raw_c.title,
                category=raw_c.category,
                text=raw_c.text,
                page_start=raw_c.page_start,
                page_end=raw_c.page_end,
                source_span=raw_c.source_span,
            )
            clauses.append(clause)
            clause_id_map[raw_c.clause_identifier] = clause.id

        # C. Obligations
        obligations: list[ExtractedObligation] = []
        for raw_o in raw_result.obligations:
            linked_clause_id = None
            if raw_o.related_clause_identifier:
                linked_clause_id = clause_id_map.get(raw_o.related_clause_identifier)
            obligation = ExtractedObligation.create(
                document_id=document_id,
                obligor=raw_o.obligor,
                duty=raw_o.duty,
                trigger=raw_o.trigger,
                deadline=raw_o.deadline,
                page_start=raw_o.page_start,
                page_end=raw_o.page_end,
                source_span=raw_o.source_span,
                clause_id=linked_clause_id,
            )
            obligations.append(obligation)

        # D. Dates
        dates: list[ExtractedDate] = [
            ExtractedDate.create(
                document_id=document_id,
                date_type=raw_d.date_type,
                raw_text=raw_d.raw_text,
                normalized_date=raw_d.normalized_date,
                description=raw_d.description,
                page_number=raw_d.page_number,
                source_span=raw_d.source_span,
            )
            for raw_d in raw_result.dates
        ]

        # E. Review Flags
        review_flags: list[ExtractedReviewFlag] = []
        for raw_f in raw_result.review_flags:
            linked_clause_id = None
            if raw_f.related_clause_identifier:
                linked_clause_id = clause_id_map.get(raw_f.related_clause_identifier)
            flag = ExtractedReviewFlag.create(
                document_id=document_id,
                flag_type=raw_f.flag_type,
                title=raw_f.title,
                description=raw_f.description,
                severity=raw_f.severity,
                page_start=raw_f.page_start,
                page_end=raw_f.page_end,
                source_span=raw_f.source_span,
                related_clause_id=linked_clause_id,
            )
            review_flags.append(flag)

        # 6. Structural & Provenance Validation
        (
            v_parties,
            v_clauses,
            v_obligations,
            v_dates,
            v_flags,
        ) = ExtractionValidator.validate_all(
            parties, clauses, obligations, dates, review_flags, pages_payload
        )

        # 7. Atomically save to repository
        understanding = self._extraction_repo.save_understanding(
            document_id=document_id,
            parties=v_parties,
            clauses=v_clauses,
            obligations=v_obligations,
            dates=v_dates,
            review_flags=v_flags,
            provider_info=raw_result.provider_info,
        )

        logger.info(
            "Structured extraction completed for doc %s: "
            "%d parties, %d clauses, %d obligations, %d dates, %d flags",
            document_id,
            len(understanding.parties),
            len(understanding.clauses),
            len(understanding.obligations),
            len(understanding.dates),
            len(understanding.review_flags),
        )

        return understanding

    def get_document_understanding(
        self, document_id: str, user_id: str
    ) -> DocumentUnderstanding | None:
        """Retrieve structured extraction facts for a document with tenant check."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            raise DocumentNotFoundError(f"Document {document_id} not found.")

        return self._extraction_repo.get_understanding_by_document(
            document_id=document_id, user_id=user_id
        )
