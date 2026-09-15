import io
import logging
from typing import Protocol

import pytesseract
from PIL import Image

from app.processing.models import OCRError
from app.processing.normalization import normalize_extracted_text

logger = logging.getLogger(__name__)


class OCRProvider(Protocol):
    """Abstract protocol for OCR optical character recognition engines."""

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from an in-memory image byte stream."""
        ...

    def is_available(self) -> bool:
        """Check whether the underlying OCR engine is available and executable."""
        ...


class TesseractOCRProvider:
    """OCR provider using the Tesseract OCR engine via pytesseract."""

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def is_available(self) -> bool:
        """Check if Tesseract executable is installed and reachable."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes using Tesseract."""
        if not image_bytes:
            return ""

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to RGB if palette or other mode
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                raw_text: str = pytesseract.image_to_string(img)
                return normalize_extracted_text(raw_text)
        except Exception as e:
            logger.warning(f"Tesseract OCR extraction failed: {e}")
            raise OCRError(f"OCR processing failed: {e}") from e


class MockOCRProvider:
    """Deterministic OCR provider for unit tests and simulation."""

    def __init__(
        self,
        mock_text: str = "Extracted text via OCR.",
        should_fail: bool = False,
    ) -> None:
        self.mock_text = mock_text
        self.should_fail = should_fail
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def is_available(self) -> bool:
        return True

    def extract_text(self, image_bytes: bytes) -> str:
        self._call_count += 1
        if self.should_fail:
            raise OCRError("Simulated OCR failure in MockOCRProvider.")
        return normalize_extracted_text(self.mock_text)
