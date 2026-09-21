"""Lawyer-Preparation Brief module for legal consultation preparation."""

from app.brief.models import (
    BriefError,
    BriefItem,
    BriefNotFoundError,
    BriefSection,
    BriefSourceType,
    DocumentNotReadyForBriefError,
    InvalidBriefStateError,
    LawyerPreparationBrief,
)
from app.brief.pdf_exporter import generate_brief_pdf
from app.brief.repository import (
    BriefRepository,
    InMemoryBriefRepository,
    PostgresBriefRepository,
    get_brief_repository,
)
from app.brief.service import BriefService, get_brief_service

__all__ = [
    "BriefError",
    "BriefItem",
    "BriefNotFoundError",
    "BriefSection",
    "BriefService",
    "BriefSourceType",
    "BriefRepository",
    "DocumentNotReadyForBriefError",
    "InMemoryBriefRepository",
    "InvalidBriefStateError",
    "LawyerPreparationBrief",
    "PostgresBriefRepository",
    "generate_brief_pdf",
    "get_brief_repository",
    "get_brief_service",
]
