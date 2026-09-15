import io

import pytest
from flask.testing import FlaskClient

from app.auth.repository import get_user_repository
from app.documents.repository import get_document_repository
from app.storage.interface import StorageSecurityError
from app.storage.local import LocalStorageService

SAMPLE_VALID_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture(autouse=True)
def setup_security_test_state() -> None:
    """Clear repositories and storage before tests."""
    get_user_repository().clear()
    get_document_repository().clear()


def create_user(client: FlaskClient, email: str, name: str) -> tuple[str, str]:
    """Register a user and return (user_id, token)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "name": name,
        },
    )
    data = resp.get_json()
    return data["user"]["user_id"], data["token"]


def test_idor_user_a_cannot_get_user_b_document(client: FlaskClient) -> None:
    """CRITICAL IDOR: User A requesting User B's document must return 404, NOT 403."""
    _, token_a = create_user(client, "usera@example.com", "User Alpha")
    _, token_b = create_user(client, "userb@example.com", "User Beta")

    # User B uploads a private document
    upload_resp = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), "user_b_private.pdf")},
        content_type="multipart/form-data",
    )
    doc_b_id = upload_resp.get_json()["document"]["document_id"]

    # User A tries to access User B's document
    response = client.get(
        f"/api/documents/{doc_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Must return 404 Not Found to prevent leaking document existence
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "not_found"


def test_idor_user_a_cannot_delete_user_b_document(client: FlaskClient) -> None:
    """CRITICAL IDOR: User A attempting to delete User B's document must return 404."""
    _, token_a = create_user(client, "usera2@example.com", "User Alpha 2")
    _, token_b = create_user(client, "userb2@example.com", "User Beta 2")

    # User B uploads a document
    upload_resp = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), "user_b_will.pdf")},
        content_type="multipart/form-data",
    )
    doc_b_id = upload_resp.get_json()["document"]["document_id"]

    # User A attempts to delete it
    response = client.delete(
        f"/api/documents/{doc_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.get_json().get("error") == "not_found"

    # Verify User B's document was NOT deleted
    verify_resp = client.get(
        f"/api/documents/{doc_b_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert verify_resp.status_code == 200


def test_list_documents_tenant_isolation(client: FlaskClient) -> None:
    """Test that listing documents returns ONLY the authenticated user's documents."""
    _, token_a = create_user(client, "usera3@example.com", "User Alpha 3")
    _, token_b = create_user(client, "userb3@example.com", "User Beta 3")

    # User A uploads 1 doc
    client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), "doc_a.pdf")},
        content_type="multipart/form-data",
    )

    # User B uploads 2 docs
    for name in ["doc_b1.pdf", "doc_b2.pdf"]:
        client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token_b}"},
            data={"file": (io.BytesIO(SAMPLE_VALID_PDF), name)},
            content_type="multipart/form-data",
        )

    # Check User A list
    resp_a = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    docs_a = resp_a.get_json()["documents"]
    assert len(docs_a) == 1
    assert docs_a[0]["filename"] == "doc_a.pdf"

    # Check User B list
    resp_b = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    docs_b = resp_b.get_json()["documents"]
    assert len(docs_b) == 2


@pytest.mark.parametrize(
    "malicious_filename",
    [
        "../secret.pdf",
        "..\\secret.pdf",
        "../../etc/passwd.pdf",
        "C:\\Windows\\System32\\calc.pdf",
        "/var/log/system.pdf",
        "doc\x00nullbyte.pdf",
        "CON.pdf",
        "PRN.pdf",
        "a" * 300 + ".pdf",
    ],
)
def test_path_traversal_filenames_are_safely_sanitized(
    client: FlaskClient, malicious_filename: str
) -> None:
    """Test that malicious filenames cannot escape storage root or inject paths."""
    _, token = create_user(client, "traversal@example.com", "Traversal Tester")

    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(SAMPLE_VALID_PDF), malicious_filename)},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    doc = response.get_json()["document"]
    # Filename must be sanitized
    assert "/" not in doc["filename"]
    assert "\\" not in doc["filename"]
    assert ".." not in doc["filename"]
    assert "\x00" not in doc["filename"]


def test_storage_service_rejects_path_traversal_keys() -> None:
    """Test that LocalStorageService raises StorageSecurityError on traversal."""
    storage = LocalStorageService()

    with pytest.raises(StorageSecurityError):
        storage._resolve_safe_path("../../../etc/passwd")

    with pytest.raises(StorageSecurityError):
        storage._resolve_safe_path("..\\..\\windows\\system32")

    with pytest.raises(StorageSecurityError):
        storage._resolve_safe_path("key\x00withnull")


def test_mime_and_magic_byte_spoofing_rejected(client: FlaskClient) -> None:
    """Test that uploading non-PDF binary files is rejected."""
    _, token = create_user(client, "spoofer@example.com", "Spoofer User")

    # ELF/executable header
    fake_exe = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00"
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(fake_exe), "invoice.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_oversized_file_rejected(client: FlaskClient) -> None:
    """Test that file exceeding max_size_bytes is rejected with 413."""
    _, token = create_user(client, "oversize@example.com", "Oversize User")

    # Construct small max limit test
    large_content = SAMPLE_VALID_PDF + (b"A" * 500)
    # Test DocumentService directly with small limit
    from app.documents.service import DocumentService

    service = DocumentService()
    file_obj = io.BytesIO(large_content)
    setattr(file_obj, "filename", "large.pdf")

    from app.documents.validation import FileTooLargeError

    with pytest.raises(FileTooLargeError):
        service.upload_document(
            user_id="any-user",
            file_obj=file_obj,
            max_size_bytes=50,
        )
