from abc import ABC, abstractmethod

from app.reasoning.models import (
    BriefReasoningRequest,
    QAReasoningRequest,
    RawBriefQuestionsResult,
    RawExtractionResult,
    RawQAResult,
    ReasoningRequest,
)


class ExtractionLLMProvider(ABC):
    """Abstract interface for structured legal extraction and grounded Q&A providers.

    All reasoning providers (deterministic development providers or neural model
    providers) implement this single boundary interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifying name of the reasoning provider."""
        pass

    @abstractmethod
    def extract_structured_data(self, request: ReasoningRequest) -> RawExtractionResult:
        """Extract structured legal entities (parties, clauses, dates, flags)."""
        pass

    @abstractmethod
    def generate_grounded_answer(self, request: QAReasoningRequest) -> RawQAResult:
        """Generate a grounded answer for a user question using retrieved evidence."""
        pass

    @abstractmethod
    def generate_brief_questions(
        self, request: BriefReasoningRequest
    ) -> RawBriefQuestionsResult:
        """Generate neutral preparation questions and checklists for consultation."""
        pass
