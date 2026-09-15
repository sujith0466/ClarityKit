from abc import ABC, abstractmethod

from app.reasoning.models import RawExtractionResult, ReasoningRequest


class ExtractionLLMProvider(ABC):
    """Abstract interface for structured legal extraction providers.

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
