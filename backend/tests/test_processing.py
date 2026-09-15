import io

import pytest
from flask.testing import FlaskClient

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.processing.extractor import PDFPageExtractor
from app.processing.models import (
    CorruptDocumentError,
    DocumentPage,
    ExtractionMethod,
    OCRError,
    PageLimitExceededError,
)
from app.processing.normalization import normalize_extracted_text
from app.processing.ocr import MockOCRProvider, TesseractOCRProvider
from app.processing.repository import InMemoryPageRepository
from app.processing.service import DocumentProcessingService
from app.storage.local import LocalStorageService
from tests.fixtures_pdf import create_scanned_synthetic_pdf, create_synthetic_pdf


def test_normalization_preserves_legal_integrity() -> None:
    """Test that normalization strips invalid characters while preserving structure."""
    raw = (
        "  \x00Section 1.01 Obligations:\r\n"
        "The Borrower shall pay $1,500,000 on January 15, 2027.\r\n\r\n\r\n\r\n"
        "\x08Clause (a): No default under Section 4.02.\x0c  "
    )
    normalized = normalize_extracted_text(raw)

    assert "\x00" not in normalized
    assert "\x08" not in normalized
    assert "\x0c" not in normalized
    assert "\r" not in normalized
    assert "Section 1.01 Obligations:\n" in normalized
    assert "The Borrower shall pay $1,500,000 on January 15, 2027." in normalized
    assert "Clause (a): No default under Section 4.02." in normalized
    # Max 2 newlines
    assert "\n\n\n" not in normalized


def test_ocr_provider_abstraction() -> None:
    """Test MockOCRProvider and TesseractOCRProvider interfaces."""
    mock_ocr = MockOCRProvider(mock_text="Scanned Signature Page")
    assert mock_ocr.is_available() is True
    assert mock_ocr.extract_text(b"fake_image") == "Scanned Signature Page"
    assert mock_ocr.call_count == 1

    failing_ocr = MockOCRProvider(should_fail=True)
    with pytest.raises(OCRError):
        failing_ocr.extract_text(b"fake_image")

    tesseract = TesseractOCRProvider()
    assert isinstance(tesseract.is_available(), bool)


def test_page_repository_idempotency() -> None:
    """Test saving pages replaces existing records idempotently."""
    repo = InMemoryPageRepository()
    doc_id = "doc-100"

    page1 = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        text="Initial Page 1",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2 = DocumentPage.create(
        document_id=doc_id,
        page_number=2,
        text="Initial Page 2",
        extraction_method=ExtractionMethod.NATIVE,
    )

    repo.save_pages(doc_id, [page1, page2])
    assert repo.count_pages(doc_id) == 2

    # Reprocess with updated text
    page1_v2 = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        text="Updated Page 1",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2_v2 = DocumentPage.create(
        document_id=doc_id,
        page_number=2,
        text="Updated Page 2",
        extraction_method=ExtractionMethod.NATIVE,
    )

    repo.save_pages(doc_id, [page1_v2, page2_v2])
    # Must still be exactly 2 pages, not 4
    assert repo.count_pages(doc_id) == 2

    pages = repo.get_pages_by_document(doc_id)
    assert len(pages) == 2
    assert pages[0].text == "Updated Page 1"
    assert pages[1].text == "Updated Page 2"

    deleted_count = repo.delete_pages_by_document(doc_id)
    assert deleted_count == 2
    assert repo.count_pages(doc_id) == 0


def test_native_text_extraction() -> None:
    """Test native PDF text extraction preserving page boundaries."""
    pdf_bytes = create_synthetic_pdf(
        [
            "First page of the commercial lease agreement between Landlord.",
            "Second page details base rent of $4,500 due on the first.",
        ]
    )

    extractor = PDFPageExtractor(ocr_provider=MockOCRProvider())
    pages = extractor.extract_document(pdf_bytes, "doc-test-1")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[0].extraction_method == ExtractionMethod.NATIVE
    assert pages[0].ocr_required is False
    assert "commercial lease agreement" in pages[0].text
    assert pages[0].word_count > 5
    assert pages[0].char_count > 30

    assert pages[1].page_number == 2
    assert pages[1].extraction_method == ExtractionMethod.NATIVE
    assert "base rent of $4,500" in pages[1].text


def test_ocr_fallback_for_scanned_page() -> None:
    """Test that a page with zero or insufficient native text triggers OCR fallback."""
    pdf_bytes = create_scanned_synthetic_pdf(page_count=1)
    mock_ocr = MockOCRProvider(mock_text="Scanned Page Signature via OCR")
    extractor = PDFPageExtractor(ocr_provider=mock_ocr)

    pages = extractor.extract_document(pdf_bytes, "doc-scanned-1")

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].extraction_method == ExtractionMethod.OCR
    assert pages[0].ocr_required is True
    assert pages[0].text == "Scanned Page Signature via OCR"


def test_mixed_native_and_ocr_document() -> None:
    """Test a document containing both native pages and scanned pages."""
    pdf_bytes = create_synthetic_pdf(
        [
            "Standard Contract Terms and Conditions Article I.",
            "",  # Empty scanned page
        ]
    )
    mock_ocr = MockOCRProvider(mock_text="Notarized Seal and Signature")
    extractor = PDFPageExtractor(ocr_provider=mock_ocr)

    pages = extractor.extract_document(pdf_bytes, "doc-mixed-1")

    assert len(pages) == 2
    assert pages[0].extraction_method == ExtractionMethod.NATIVE
    assert pages[0].ocr_required is False
    assert "Standard Contract Terms" in pages[0].text

    assert pages[1].extraction_method == ExtractionMethod.OCR
    assert pages[1].ocr_required is True
    assert "Notarized Seal" in pages[1].text


def test_processing_service_end_to_end(tmp_path: pytest.TempPathFactory) -> None:
    """Test complete end-to-end processing service execution and state transitions."""
    storage = LocalStorageService(root_dir=str(tmp_path))
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    mock_ocr = MockOCRProvider()

    service = DocumentProcessingService(
        document_repository=doc_repo,
        page_repository=page_repo,
        storage_service=storage,
        ocr_provider=mock_ocr,
    )

    user_id = "u-user-123"
    pdf_bytes = create_synthetic_pdf(
        ["Loan Agreement Promissory Note with clear legal commitments."]
    )
    key = storage.generate_storage_key(user_id=user_id, document_id="doc-1")
    storage.save(key, pdf_bytes)

    doc = Document(
        user_id=user_id,
        filename="loan.pdf",
        storage_key=key,
        file_size_bytes=len(pdf_bytes),
        content_type="application/pdf",
        content_hash="hash123",
        status=DocumentStatus.QUEUED,
    )
    doc_repo.save(doc)

    # Execute processing
    pages = service.process_document(user_id=user_id, document_id=doc.id)

    assert len(pages) == 1
    assert pages[0].text.startswith("Loan Agreement")

    # Document state should be READY
    updated_doc = doc_repo.get_by_id(doc.id)
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.READY
    assert updated_doc.error_message is None

    # Retrieve pages via service
    retrieved_pages = service.get_document_pages(user_id=user_id, document_id=doc.id)
    assert retrieved_pages is not None
    assert len(retrieved_pages) == 1

    # Processing summary
    summary = service.get_processing_summary(user_id=user_id, document_id=doc.id)
    assert summary is not None
    assert summary["status"] == "READY"
    assert summary["page_count"] == 1
    assert summary["native_page_count"] == 1
    assert summary["ocr_page_count"] == 0


def test_processing_service_corrupt_pdf_failure(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Test that processing corrupt PDF marks document as FAILED."""
    storage = LocalStorageService(root_dir=str(tmp_path))
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()

    service = DocumentProcessingService(
        document_repository=doc_repo,
        page_repository=page_repo,
        storage_service=storage,
    )

    user_id = "u-user-456"
    bad_bytes = b"%PDF-1.4\ncorrupted content that cannot be parsed by pdf reader"
    key = storage.generate_storage_key(user_id=user_id, document_id="doc-bad")
    storage.save(key, bad_bytes)

    doc = Document(
        user_id=user_id,
        filename="bad.pdf",
        storage_key=key,
        file_size_bytes=len(bad_bytes),
        content_type="application/pdf",
        content_hash="hash456",
        status=DocumentStatus.QUEUED,
    )
    doc_repo.save(doc)

    with pytest.raises(CorruptDocumentError):
        service.process_document(user_id=user_id, document_id=doc.id)

    updated_doc = doc_repo.get_by_id(doc.id)
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.FAILED
    assert updated_doc.error_message is not None


def test_processing_service_oversized_page_limit(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Test that a document exceeding max_pages is rejected."""
    storage = LocalStorageService(root_dir=str(tmp_path))
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()

    service = DocumentProcessingService(
        document_repository=doc_repo,
        page_repository=page_repo,
        storage_service=storage,
        max_pages=2,  # Set small limit
    )

    user_id = "u-user-789"
    pdf_bytes = create_synthetic_pdf(["Page 1", "Page 2", "Page 3"])
    key = storage.generate_storage_key(user_id=user_id, document_id="doc-too-many")
    storage.save(key, pdf_bytes)

    doc = Document(
        user_id=user_id,
        filename="many_pages.pdf",
        storage_key=key,
        file_size_bytes=len(pdf_bytes),
        content_type="application/pdf",
        content_hash="hash789",
        status=DocumentStatus.QUEUED,
    )
    doc_repo.save(doc)

    with pytest.raises(PageLimitExceededError):
        service.process_document(user_id=user_id, document_id=doc.id)

    updated_doc = doc_repo.get_by_id(doc.id)
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.FAILED


def test_processing_api_endpoints(client: FlaskClient) -> None:
    """Test HTTP API routes for document processing and pages retrieval."""
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "processor@example.com",
            "password": "SecurePass123!",
            "name": "Processor User",
        },
    )
    token = reg_res.get_json()["token"]

    pdf_bytes = create_synthetic_pdf(
        ["Page 1 contract text with sufficient length for native extraction."]
    )

    # 1. Upload document
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(pdf_bytes), "sample_contract.pdf")},
        content_type="multipart/form-data",
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.get_json()["document"]["id"]

    # 2. Trigger processing
    proc_res = client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert proc_res.status_code == 200
    proc_data = proc_res.get_json()
    assert proc_data["status"] == "success"
    assert proc_data["page_count"] == 1
    assert len(proc_data["pages"]) == 1
    assert "Page 1 contract text" in proc_data["pages"][0]["text"]

    # 3. Retrieve pages
    pages_res = client.get(
        f"/api/documents/{doc_id}/pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pages_res.status_code == 200
    pages_data = pages_res.get_json()
    assert pages_data["count"] == 1
    assert pages_data["pages"][0]["page_number"] == 1

    # 4. Retrieve processing summary
    summary_res = client.get(
        f"/api/documents/{doc_id}/processing",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.get_json()["processing"]
    assert summary_data["status"] == "READY"
    assert summary_data["page_count"] == 1
