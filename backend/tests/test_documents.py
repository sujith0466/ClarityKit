import io

import pytest
from flask.testing import FlaskClient

from app.auth.repository import get_user_repository
from app.documents.repository import get_document_repository
from app.storage.local import get_storage_service

# Valid minimal PDF payload with %PDF- header
SAMPLE_VALID_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture(autouse=True)
def setup_test_environment() -> None:
    """Clear repositories and storage state before each test."""
    get_user_repository().clear()
    get_document_repository().clear()


def create_authenticated_user(
    client: FlaskClient,
    email: str = "attorney@example.com",
    name: str = "Attorney User",
) -> tuple[str, str]:
    """Helper to create a user and return (user_id, auth_token)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123",
            "name": name,
        },
    )
    data = resp.get_json()
    return data["user"]["user_id"], data["token"]


def test_upload_valid_pdf_success(client: FlaskClient) -> None:
    """Test authenticated upload of a valid PDF document."""
    _, token = create_authenticated_user(client)

    data = {
        "file": (io.BytesIO(SAMPLE_VALID_PDF), "employment_agreement.pdf"),
    }
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    result = response.get_json()
    assert result is not None
    assert result.get("status") == "success"
    doc = result.get("document", {})
    assert doc.get("filename") == "employment_agreement.pdf"
    assert doc.get("content_type") == "application/pdf"
    assert doc.get("status") == "QUEUED"
    assert doc.get("file_size_bytes") == len(SAMPLE_VALID_PDF)
    assert "document_id" in doc
    # Critical: storage_key / internal filesystem path must NOT be leaked
    assert "storage_key" not in doc
    assert "root_dir" not in doc


def test_upload_unauthenticated_returns_401(client: FlaskClient) -> None:
    """Test unauthenticated document upload returns 401."""
    data = {
        "file": (io.BytesIO(SAMPLE_VALID_PDF), "contract.pdf"),
    }
    response = client.post(
        "/api/documents",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 401
    assert response.get_json().get("error") == "unauthorized"


def test_upload_missing_file_returns_400(client: FlaskClient) -> None:
    """Test upload without file field returns 400."""
    _, token = create_authenticated_user(client)

    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json().get("error") == "validation_error"


def test_upload_empty_file_returns_400(client: FlaskClient) -> None:
    """Test uploading an empty (0 byte) file returns 400."""
    _, token = create_authenticated_user(client)

    data = {
        "file": (io.BytesIO(b""), "empty.pdf"),
    }
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json().get("error") == "validation_error"


def test_upload_invalid_signature_returns_400(client: FlaskClient) -> None:
    """Test uploading non-PDF content with .pdf extension returns 400."""
    _, token = create_authenticated_user(client)

    fake_content = b"This is plain text without PDF header signature."
    data = {
        "file": (io.BytesIO(fake_content), "fake.pdf"),
    }
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json().get("error") == "validation_error"


def test_upload_unsupported_extension_returns_400(client: FlaskClient) -> None:
    """Test uploading non-PDF extension returns 400."""
    _, token = create_authenticated_user(client)

    data = {
        "file": (io.BytesIO(SAMPLE_VALID_PDF), "contract.docx"),
    }
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json().get("error") == "validation_error"


def test_list_documents(client: FlaskClient) -> None:
    """Test listing documents returns all documents owned by the user."""
    _, token = create_authenticated_user(client)

    # Upload two documents
    for name in ["doc1.pdf", "doc2.pdf"]:
        client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            data={"file": (io.BytesIO(SAMPLE_VALID_PDF), name)},
            content_type="multipart/form-data",
        )

    response = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["count"] == 2
    assert len(data["documents"]) == 2


def test_get_document_detail(client: FlaskClient) -> None:
    """Test retrieving document detail by document_id."""
    _, token = create_authenticated_user(client)

    upload_resp = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), "nda.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_resp.get_json()["document"]["document_id"]

    response = client.get(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["document"]["document_id"] == doc_id
    assert data["document"]["filename"] == "nda.pdf"


def test_delete_document(client: FlaskClient) -> None:
    """Test deleting document removes it and cleans up storage."""
    _, token = create_authenticated_user(client)

    upload_resp = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), "lease.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_resp.get_json()["document"]["document_id"]

    # Verify document exists in repo
    doc = get_document_repository().get_by_id(doc_id)
    assert doc is not None
    assert get_storage_service().exists(doc.storage_key) is True

    # Delete
    response = client.delete(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"

    # Verify storage file is removed
    assert get_storage_service().exists(doc.storage_key) is False

    # Verify subsequent GET returns 404
    get_resp = client.get(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 404
