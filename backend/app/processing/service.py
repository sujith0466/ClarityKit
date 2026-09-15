import logging
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.processing.extractor import DEFAULT_MAX_PAGES, PDFPageExtractor
from app.processing.models import (
    CorruptDocumentError,
    DocumentPage,
    InvalidDocumentStateError,
    PageLimitExceededError,
    ProcessingError,
)
from app.processing.ocr import OCRProvider, TesseractOCRProvider
from app.processing.repository import (
    PageRepository,
    in_memory_page_repository,
)
from app.storage.interface import StorageService
from app.storage.local import default_storage_service

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Orchestrates document content extraction, OCR fallback, and state management."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        storage_service: StorageService | None = None,
        ocr_provider: OCRProvider | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._storage = storage_service or default_storage_service
        self._ocr = ocr_provider or TesseractOCRProvider()
        self._extractor = PDFPageExtractor(
            ocr_provider=self._ocr,
            max_pages=max_pages,
        )

    def process_document(self, user_id: str, document_id: str) -> list[DocumentPage]:
        """Process an uploaded PDF: extract pages, OCR fallback, update status.

        Returns extracted DocumentPage instances.
        Raises:
            ProcessingError on failure.
        """
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return []

        if doc.status == DocumentStatus.UPLOADING:
            raise InvalidDocumentStateError(
                f"Document '{document_id}' is still uploading and cannot be processed."
            )

        # Transition state to PROCESSING
        self._doc_repo.update_status(document_id, DocumentStatus.PROCESSING)

        try:
            # 1. Fetch binary data from secure storage
            pdf_bytes = self._storage.get(doc.storage_key)
            if pdf_bytes is None:
                raise CorruptDocumentError(
                    f"Stored binary file not found for document '{document_id}'."
                )

            # 2. Extract page contents with OCR fallback
            pages = self._extractor.extract_document(pdf_bytes, document_id)

            # 3. Persist extracted pages idempotently
            saved_pages = self._page_repo.save_pages(document_id, pages)

            # 4. Update document status to READY
            self._doc_repo.update_status(document_id, DocumentStatus.READY)
            return saved_pages

        except (CorruptDocumentError, PageLimitExceededError) as e:
            logger.warning(f"Processing validation failed for doc {document_id}: {e}")
            self._doc_repo.update_status(
                document_id, DocumentStatus.FAILED, error_message=str(e)
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected processing error for doc {document_id}: {e}",
                exc_info=True,
            )
            self._doc_repo.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_message="An internal error occurred during document processing.",
            )
            raise ProcessingError(f"Document processing failed: {e}") from e

    def get_document_pages(
        self, user_id: str, document_id: str
    ) -> list[DocumentPage] | None:
        """Retrieve all extracted pages for a document owned by the user."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return None

        return self._page_repo.get_pages_by_document(document_id)

    def get_processing_summary(
        self, user_id: str, document_id: str
    ) -> dict[str, Any] | None:
        """Retrieve processing metadata and summary for a document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return None

        pages = self._page_repo.get_pages_by_document(document_id)
        ocr_page_count = sum(1 for p in pages if p.extraction_method.value == "ocr")

        return {
            "document_id": doc.id,
            "status": doc.status.value,
            "page_count": len(pages),
            "ocr_page_count": ocr_page_count,
            "native_page_count": len(pages) - ocr_page_count,
            "error_message": doc.error_message,
            "updated_at": doc.updated_at,
        }


# Global singleton service instance for in-memory foundation
default_processing_service = DocumentProcessingService()
