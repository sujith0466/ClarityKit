import hashlib

from app.processing.models import DocumentPage, ExtractionMethod
from app.retrieval.chunker import ChunkingConfig, DocumentChunker


def _make_page(
    page_number: int,
    text: str,
    doc_id: str = "doc-1",
    page_id: str | None = None,
) -> DocumentPage:
    """Helper to construct a valid DocumentPage."""
    return DocumentPage.create(
        document_id=doc_id,
        page_number=page_number,
        text=text,
        extraction_method=ExtractionMethod.NATIVE,
        page_id=page_id or f"page-id-{doc_id}-{page_number}",
    )


def test_chunker_empty_document_handling() -> None:
    """Test that empty or blank pages produce zero chunks without errors."""
    chunker = DocumentChunker()

    assert chunker.chunk_document("doc-empty", []) == []

    p_blank = _make_page(1, "   \n\n  \t  ")
    assert chunker.chunk_document("doc-blank", [p_blank]) == []


def test_chunker_single_short_page() -> None:
    """Test single page with text shorter than target chunk size."""
    text = (
        "This Commercial Lease Agreement is made and entered into on "
        "January 15, 2026, by and between Landlord and Tenant."
    )
    page = _make_page(1, text)
    chunker = DocumentChunker(ChunkingConfig(target_chunk_size=600, chunk_overlap=120))

    chunks = chunker.chunk_document("doc-short", [page])

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "doc-short"
    assert chunk.chunk_index == 0
    assert chunk.page_start == 1
    assert chunk.page_end == 1
    assert chunk.source_page_ids == [page.id]
    assert chunk.text == text
    assert chunk.content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_chunker_deterministic_output() -> None:
    """Test that same pages and config produce identical chunk sequences."""
    text1 = (
        "Section 1. Term and Renewal. The term of this Lease shall be "
        "36 months starting March 1, 2026."
    )
    text2 = (
        "Section 2. Base Rent. Tenant shall pay Base Rent of $5,000.00 USD "
        "on or before the first day of each month."
    )
    pages = [_make_page(1, text1), _make_page(2, text2)]

    chunker = DocumentChunker(
        ChunkingConfig(target_chunk_size=100, chunk_overlap=30, min_chunk_size=40)
    )

    run1 = chunker.chunk_document("doc-det", pages)
    run2 = chunker.chunk_document("doc-det", pages)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2, strict=True):
        assert c1.chunk_index == c2.chunk_index
        assert c1.text == c2.text
        assert c1.page_start == c2.page_start
        assert c1.page_end == c2.page_end
        assert c1.content_hash == c2.content_hash


def test_chunker_cross_page_provenance() -> None:
    """Test that cross-page text records page_start and page_end."""
    page1_text = (
        "Article IV: Indemnification and Liability. "
        "The Borrower agrees to defend, indemnify, and hold harmless "
        "the Lender and its officers, directors, and agents."
    )
    page2_text = (
        "Such indemnification shall survive the termination of this Agreement "
        "and the full payment of the Obligations hereunder."
    )
    pages = [
        _make_page(3, page1_text, page_id="p-3"),
        _make_page(4, page2_text, page_id="p-4"),
    ]

    # Target chunk size spans across both pages
    chunker = DocumentChunker(
        ChunkingConfig(target_chunk_size=400, chunk_overlap=80, min_chunk_size=50)
    )
    chunks = chunker.chunk_document("doc-cross", pages)

    assert len(chunks) >= 1
    # Check that cross-page chunk captures page 3 to 4
    cross_chunk = chunks[0]
    assert cross_chunk.page_start == 3
    assert cross_chunk.page_end == 4
    assert "p-3" in cross_chunk.source_page_ids
    assert "p-4" in cross_chunk.source_page_ids
    assert "Article IV" in cross_chunk.text
    assert "Such indemnification shall survive" in cross_chunk.text


def test_chunker_source_text_integrity() -> None:
    """Test that numbers, dates, punctuation, and legal terms are preserved exactly."""
    verbatim_text = (
        "Clause 12.3: Failure to pay within thirty (30) calendar days "
        "shall incur a penalty of 5.75% per annum or $1,250.00 USD, "
        "whichever is greater, effective as of 2026-10-01."
    )
    page = _make_page(1, verbatim_text)
    chunker = DocumentChunker()

    chunks = chunker.chunk_document("doc-verbatim", [page])

    assert len(chunks) == 1
    assert chunks[0].text == verbatim_text
    assert "30" in chunks[0].text
    assert "5.75%" in chunks[0].text
    assert "$1,250.00 USD" in chunks[0].text
    assert "2026-10-01" in chunks[0].text
