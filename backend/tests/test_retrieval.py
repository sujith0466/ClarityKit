import io

import pytest
from flask.testing import FlaskClient

from app.documents.models import Document, DocumentStatus
from app.documents.repository import InMemoryDocumentRepository
from app.processing.models import DocumentPage, ExtractionMethod
from app.processing.repository import InMemoryPageRepository
from app.retrieval.chunker import DocumentChunker
from app.retrieval.embeddings import DeterministicEmbeddingProvider
from app.retrieval.indexing_service import IndexingService
from app.retrieval.models import IndexingError, InvalidQueryError
from app.retrieval.repository import InMemoryVectorChunkRepository
from app.retrieval.retrieval_service import RetrievalService
from tests.fixtures_pdf import create_synthetic_pdf


def test_indexing_service_and_retrieval_end_to_end() -> None:
    """Test full indexing pipeline from pages to semantic retrieval."""
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    chunk_repo = InMemoryVectorChunkRepository(document_repository=doc_repo)
    provider = DeterministicEmbeddingProvider()

    indexing_service = IndexingService(
        document_repository=doc_repo,
        page_repository=page_repo,
        chunk_repository=chunk_repo,
        chunker=DocumentChunker(),
        embedding_provider=provider,
    )

    retrieval_service = RetrievalService(
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
        embedding_provider=provider,
    )

    user_id = "u-user-ret-1"
    doc = Document(
        user_id=user_id,
        filename="service_agreement.pdf",
        storage_key="k1",
        file_size_bytes=1000,
        content_type="application/pdf",
        content_hash="h1",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page1 = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text="Section 1: The Service Provider shall deliver engineering services.",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page2 = DocumentPage.create(
        document_id=doc.id,
        page_number=2,
        text="Section 2: Payment terms shall be Net 30 days upon invoice receipt.",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page1, page2])

    # 1. Index document
    indexed_chunks = indexing_service.index_document(user_id, doc.id)
    assert len(indexed_chunks) >= 1
    assert chunk_repo.count_chunks(doc.id) == len(indexed_chunks)

    # 2. Retrieve by semantic query
    results = retrieval_service.retrieve(
        user_id=user_id,
        query="engineering services delivery",
        top_k=2,
    )
    assert len(results) >= 1
    top_result = results[0]
    assert top_result.document_id == doc.id
    assert "engineering services" in top_result.text
    assert top_result.similarity > 0.0

    # 3. Retrieve with document filter
    scoped_results = retrieval_service.retrieve(
        user_id=user_id,
        query="Payment terms Net 30 days invoice",
        document_id=doc.id,
        top_k=1,
    )
    assert len(scoped_results) == 1
    assert "Payment terms" in scoped_results[0].text

    # 4. Summary inspection
    summary = indexing_service.get_indexing_summary(user_id, doc.id)
    assert summary is not None
    assert summary["status"] == "indexed"
    assert summary["chunk_count"] == len(indexed_chunks)


def test_indexing_idempotency() -> None:
    """Test re-indexing a document replaces chunks without duplicates."""
    doc_repo = InMemoryDocumentRepository()
    page_repo = InMemoryPageRepository()
    chunk_repo = InMemoryVectorChunkRepository(document_repository=doc_repo)

    indexing_service = IndexingService(
        document_repository=doc_repo,
        page_repository=page_repo,
        chunk_repository=chunk_repo,
    )

    user_id = "u-user-idem"
    doc = Document(
        user_id=user_id,
        filename="reindex_test.pdf",
        storage_key="k2",
        file_size_bytes=500,
        content_type="application/pdf",
        content_hash="h2",
        status=DocumentStatus.READY,
    )
    doc_repo.save(doc)

    page = DocumentPage.create(
        document_id=doc.id,
        page_number=1,
        text="Original contract text for initial indexing.",
        extraction_method=ExtractionMethod.NATIVE,
    )
    page_repo.save_pages(doc.id, [page])

    # First indexing
    chunks1 = indexing_service.index_document(user_id, doc.id)
    assert len(chunks1) == 1
    assert chunk_repo.count_chunks(doc.id) == 1

    # Second indexing (same document)
    chunks2 = indexing_service.index_document(user_id, doc.id)
    assert len(chunks2) == 1
    assert chunk_repo.count_chunks(doc.id) == 1


def test_indexing_unready_document_rejected() -> None:
    """Test indexing a QUEUED or PROCESSING document raises IndexingError."""
    doc_repo = InMemoryDocumentRepository()
    indexing_service = IndexingService(document_repository=doc_repo)

    user_id = "u-user-unready"
    doc = Document(
        user_id=user_id,
        filename="unready.pdf",
        storage_key="k3",
        file_size_bytes=500,
        content_type="application/pdf",
        content_hash="h3",
        status=DocumentStatus.QUEUED,
    )
    doc_repo.save(doc)

    with pytest.raises(IndexingError):
        indexing_service.index_document(user_id, doc.id)


def test_retrieval_query_validation_bounds() -> None:
    """Test query length and top_k bounds validation."""
    doc_repo = InMemoryDocumentRepository()
    retrieval_service = RetrievalService(document_repository=doc_repo)
    user_id = "u-user-bounds"

    # Empty query
    with pytest.raises(InvalidQueryError):
        retrieval_service.retrieve(user_id, "   ")

    # Oversized query (> 1000 chars)
    oversized = "a" * 1001
    with pytest.raises(InvalidQueryError):
        retrieval_service.retrieve(user_id, oversized)

    # Invalid top_k (0 or negative)
    with pytest.raises(InvalidQueryError):
        retrieval_service.retrieve(user_id, "valid query", top_k=0)

    # Excessive top_k (> 50)
    with pytest.raises(InvalidQueryError):
        retrieval_service.retrieve(user_id, "valid query", top_k=51)


def test_retrieval_api_endpoints(client: FlaskClient) -> None:
    """Test HTTP API routes for document indexing, chunk retrieval, and search."""
    # 1. Register user
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "retrieval_tester@example.com",
            "password": "StrongSecurity123!",
            "name": "Retrieval User",
        },
    )
    token = reg_res.get_json()["token"]

    pdf_bytes = create_synthetic_pdf(
        [
            "Clause 1: Confidentiality covers all proprietary technical data.",
            "Clause 2: Each Party agrees to protect the Confidential Information.",
        ]
    )

    # 2. Upload document
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(pdf_bytes), "nda_agreement.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_res.get_json()["document"]["id"]

    # 3. Process document (Phase 4)
    proc_res = client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert proc_res.status_code == 200

    # 4. Trigger Indexing (Phase 5)
    index_res = client.post(
        f"/api/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert index_res.status_code == 200
    index_data = index_res.get_json()
    assert index_data["status"] == "success"
    assert index_data["chunk_count"] >= 1

    # 5. Retrieve indexed chunks
    chunks_res = client.get(
        f"/api/documents/{doc_id}/chunks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chunks_res.status_code == 200
    chunks_data = chunks_res.get_json()
    assert chunks_data["count"] >= 1
    assert "Confidential Information" in chunks_data["chunks"][0]["text"]

    # 6. Retrieve indexing summary
    summary_res = client.get(
        f"/api/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_res.status_code == 200
    assert summary_res.get_json()["indexing"]["status"] == "indexed"

    # 7. Execute semantic search
    search_res = client.post(
        "/api/retrieval/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "proprietary technical and commercial data",
            "top_k": 3,
        },
    )
    assert search_res.status_code == 200
    search_data = search_res.get_json()
    assert search_data["status"] == "success"
    assert search_data["count"] >= 1
    assert "Confidential Information" in search_data["results"][0]["text"]
    assert "similarity" in search_data["results"][0]
