import logging

from app.reasoning.deterministic_provider import (
    DeterministicStructuredExtractionProvider,
)
from app.reasoning.models import (
    QAReasoningRequest,
    RawExtractionResult,
    RawQAResult,
    ReasoningRequest,
)
from app.reasoning.provider import ExtractionLLMProvider

logger = logging.getLogger(__name__)


class ReasoningGateway:
    """Central gateway boundary for generative/extraction reasoning tasks.

    All application modules requiring LLM reasoning must route
    through ReasoningGateway to enforce isolation and uniform interfaces.
    """

    def __init__(self, provider: ExtractionLLMProvider | None = None) -> None:
        self._provider: ExtractionLLMProvider = (
            provider
            if provider is not None
            else DeterministicStructuredExtractionProvider()
        )

    @property
    def provider(self) -> ExtractionLLMProvider:
        return self._provider

    def extract_structured_data(self, request: ReasoningRequest) -> RawExtractionResult:
        """Route extraction request to the configured provider."""
        logger.info(
            "Executing structured extraction for document %s via provider %s",
            request.document_id,
            self._provider.provider_name,
        )
        return self._provider.extract_structured_data(request)

    def generate_grounded_answer(self, request: QAReasoningRequest) -> RawQAResult:
        """Route Q&A reasoning request to the configured provider."""
        logger.info(
            "Generating grounded answer for document %s query via provider %s",
            request.document_id,
            self._provider.provider_name,
        )
        return self._provider.generate_grounded_answer(request)


# Singleton gateway instance for default runtime
default_reasoning_gateway = ReasoningGateway()


def get_reasoning_gateway() -> ReasoningGateway:
    """Return active ReasoningGateway instance."""
    return default_reasoning_gateway
