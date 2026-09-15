import io
import logging
import time

import pypdf
from pypdf.errors import PdfReadError

from app.processing.models import (
    CorruptDocumentError,
    DocumentPage,
    ExtractionMethod,
    PageLimitExceededError,
)
from app.processing.normalization import normalize_extracted_text
from app.processing.ocr import OCRProvider

logger = logging.getLogger(__name__)

DEFAULT_MAX_PAGES = 500
DEFAULT_NATIVE_CHAR_THRESHOLD = 30


class PDFPageExtractor:
    """Extracts text on a per-page basis with native extraction and OCR fallback."""

    def __init__(
        self,
        ocr_provider: OCRProvider,
        max_pages: int = DEFAULT_MAX_PAGES,
        native_char_threshold: int = DEFAULT_NATIVE_CHAR_THRESHOLD,
    ) -> None:
        self.ocr_provider = ocr_provider
        self.max_pages = max_pages
        self.native_char_threshold = native_char_threshold

    def extract_document(
        self,
        pdf_bytes: bytes,
        document_id: str,
    ) -> list[DocumentPage]:
        """Extract all pages from a PDF document byte stream.

        Returns a list of DocumentPage instances preserving page order and
        extraction methodology.
        """
        if not pdf_bytes:
            raise CorruptDocumentError("Empty PDF byte stream provided.")

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except (PdfReadError, Exception) as e:
            logger.warning(f"Failed to parse PDF for document {document_id}: {e}")
            raise CorruptDocumentError(f"Corrupt or invalid PDF file: {e}") from e

        if reader.is_encrypted:
            raise CorruptDocumentError(
                "Encrypted or password-protected PDFs are not supported."
            )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise CorruptDocumentError("The PDF document contains 0 pages.")

        if total_pages > self.max_pages:
            raise PageLimitExceededError(
                f"Document contains {total_pages} pages, "
                f"which exceeds the limit of {self.max_pages}."
            )

        extracted_pages: list[DocumentPage] = []

        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1
            start_time = time.perf_counter()

            # 1. Attempt native text extraction
            try:
                native_raw = page.extract_text() or ""
            except Exception as e:
                logger.debug(f"Native extraction exception on page {page_number}: {e}")
                native_raw = ""

            normalized_native = normalize_extracted_text(native_raw)
            meaningful_char_count = len(
                normalized_native.replace(" ", "").replace("\n", "")
            )

            # 2. Check if OCR fallback is required
            if meaningful_char_count < self.native_char_threshold:
                # Scanned or image-only page
                ocr_text = self._extract_page_ocr(page, page_number, document_id)
                normalized_ocr = normalize_extracted_text(ocr_text)

                # If OCR produced text, use OCR result; otherwise fallback to native
                final_text = normalized_ocr if normalized_ocr else normalized_native
                method = (
                    ExtractionMethod.OCR if normalized_ocr else ExtractionMethod.NATIVE
                )
                ocr_required = True
            else:
                final_text = normalized_native
                method = ExtractionMethod.NATIVE
                ocr_required = False

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            doc_page = DocumentPage.create(
                document_id=document_id,
                page_number=page_number,
                text=final_text,
                extraction_method=method,
                ocr_required=ocr_required,
                processing_duration_ms=round(duration_ms, 2),
            )
            extracted_pages.append(doc_page)

        return extracted_pages

    def _extract_page_ocr(
        self,
        page: pypdf.PageObject,
        page_number: int,
        document_id: str,
    ) -> str:
        """Extract OCR text from embedded images on the page."""
        ocr_texts: list[str] = []

        try:
            images = list(getattr(page, "images", []))
            if images:
                for img in images:
                    img_bytes = getattr(img, "data", None)
                    if img_bytes:
                        text = self.ocr_provider.extract_text(img_bytes)
                        if text:
                            ocr_texts.append(text)
            else:
                fallback_text = self.ocr_provider.extract_text(b"")
                if fallback_text:
                    ocr_texts.append(fallback_text)
        except Exception as e:
            logger.warning(
                f"OCR extraction encountered an issue on doc "
                f"{document_id} page {page_number}: {e}"
            )

        return "\n\n".join(ocr_texts)
