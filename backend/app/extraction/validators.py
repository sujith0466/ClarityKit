import logging
from typing import Any

from app.extraction.models import (
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
    InvalidExtractionSchemaError,
)

logger = logging.getLogger(__name__)


class ExtractionValidator:
    """Validates structural constraints and provenance for extracted entities."""

    @staticmethod
    def validate_party(
        party: ExtractedParty, page_texts: dict[int, str]
    ) -> ExtractedParty:
        if not party.name or not party.name.strip():
            raise InvalidExtractionSchemaError("Extracted party name cannot be empty.")
        if party.page_number not in page_texts:
            logger.warning(
                "Party %s references page %d not in document pages %s",
                party.name,
                party.page_number,
                list(page_texts.keys()),
            )
        return party

    @staticmethod
    def validate_clause(
        clause: ExtractedClause, page_texts: dict[int, str]
    ) -> ExtractedClause:
        if not clause.title or not clause.title.strip():
            raise InvalidExtractionSchemaError(
                "Extracted clause title cannot be empty."
            )
        if not clause.text or not clause.text.strip():
            raise InvalidExtractionSchemaError("Extracted clause text cannot be empty.")
        return clause

    @staticmethod
    def validate_obligation(
        obligation: ExtractedObligation, page_texts: dict[int, str]
    ) -> ExtractedObligation:
        if not obligation.duty or not obligation.duty.strip():
            raise InvalidExtractionSchemaError(
                "Extracted obligation duty cannot be empty."
            )
        return obligation

    @staticmethod
    def validate_date(date: ExtractedDate, page_texts: dict[int, str]) -> ExtractedDate:
        if not date.raw_text or not date.raw_text.strip():
            raise InvalidExtractionSchemaError(
                "Extracted date raw_text cannot be empty."
            )
        return date

    @staticmethod
    def validate_review_flag(
        flag: ExtractedReviewFlag, page_texts: dict[int, str]
    ) -> ExtractedReviewFlag:
        if not flag.title or not flag.title.strip():
            raise InvalidExtractionSchemaError("Review flag title cannot be empty.")
        if not flag.description or not flag.description.strip():
            raise InvalidExtractionSchemaError(
                "Review flag description cannot be empty."
            )
        return flag

    @classmethod
    def validate_all(
        cls,
        parties: list[ExtractedParty],
        clauses: list[ExtractedClause],
        obligations: list[ExtractedObligation],
        dates: list[ExtractedDate],
        review_flags: list[ExtractedReviewFlag],
        pages: list[dict[str, Any]],
    ) -> tuple[
        list[ExtractedParty],
        list[ExtractedClause],
        list[ExtractedObligation],
        list[ExtractedDate],
        list[ExtractedReviewFlag],
    ]:
        page_texts: dict[int, str] = {
            p.get("page_number", idx + 1): p.get("text", "")
            for idx, p in enumerate(pages)
        }

        valid_parties = [cls.validate_party(p, page_texts) for p in parties]
        valid_clauses = [cls.validate_clause(c, page_texts) for c in clauses]
        valid_obligations = [
            cls.validate_obligation(o, page_texts) for o in obligations
        ]
        valid_dates = [cls.validate_date(d, page_texts) for d in dates]
        valid_flags = [cls.validate_review_flag(f, page_texts) for f in review_flags]

        return (
            valid_parties,
            valid_clauses,
            valid_obligations,
            valid_dates,
            valid_flags,
        )
