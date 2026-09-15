import io

from flask.testing import FlaskClient

from tests.fixtures_pdf import create_synthetic_pdf


def create_user_and_token(
    client: FlaskClient, email: str, name: str
) -> tuple[str, str]:
    """Helper to create a user and return (user_id, token)."""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "StrongSecurityPass123!",
            "name": name,
        },
    )
    data = resp.get_json()
    return data["user"]["user_id"], data["token"]


def test_unauthenticated_processing_endpoints_rejected(
    client: FlaskClient,
) -> None:
    """Test that all Phase 4 endpoints strictly require authentication (401)."""
    doc_id = "doc-unauth-123"

    res_post = client.post(f"/api/documents/{doc_id}/process")
    assert res_post.status_code == 401
    assert res_post.get_json()["error"] == "unauthorized"

    res_pages = client.get(f"/api/documents/{doc_id}/pages")
    assert res_pages.status_code == 401
    assert res_pages.get_json()["error"] == "unauthorized"

    res_proc = client.get(f"/api/documents/{doc_id}/processing")
    assert res_proc.status_code == 401
    assert res_proc.get_json()["error"] == "unauthorized"


def test_cross_tenant_idor_process_returns_404(client: FlaskClient) -> None:
    """Test that User B cannot trigger processing on User A's document (returns 404)."""
    user_a_id, token_a = create_user_and_token(client, "alice@example.com", "Alice A")
    user_b_id, token_b = create_user_and_token(client, "bob@example.com", "Bob B")

    pdf_bytes = create_synthetic_pdf(
        ["Alice Confidential Terms and Conditions Agreement."]
    )

    # Alice uploads document
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"file": (io.BytesIO(pdf_bytes), "alice_confidential.pdf")},
        content_type="multipart/form-data",
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.get_json()["document"]["id"]

    # Bob attempts to trigger processing on Alice's document -> 404
    bob_process_res = client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert bob_process_res.status_code == 404
    assert bob_process_res.get_json()["error"] == "not_found"

    # Bob attempts to get pages for Alice's document -> 404
    bob_pages_res = client.get(
        f"/api/documents/{doc_id}/pages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert bob_pages_res.status_code == 404
    assert bob_pages_res.get_json()["error"] == "not_found"

    # Bob attempts to get processing summary -> 404
    bob_summary_res = client.get(
        f"/api/documents/{doc_id}/processing",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert bob_summary_res.status_code == 404
    assert bob_summary_res.get_json()["error"] == "not_found"


def test_nonexistent_document_processing_returns_404(
    client: FlaskClient,
) -> None:
    """Test that operations on nonexistent document ID return 404."""
    _, token = create_user_and_token(client, "user1@example.com", "User One")
    fake_id = "00000000-0000-0000-0000-000000000000"

    res_post = client.post(
        f"/api/documents/{fake_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_post.status_code == 404

    res_pages = client.get(
        f"/api/documents/{fake_id}/pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_pages.status_code == 404

    res_proc = client.get(
        f"/api/documents/{fake_id}/processing",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_proc.status_code == 404


def test_document_deletion_cascades_and_prevents_page_access(
    client: FlaskClient,
) -> None:
    """Test that deleted documents clean up pages and return 404."""
    _, token = create_user_and_token(client, "deleter@example.com", "Deleter User")

    pdf_bytes = create_synthetic_pdf(["Deletable contract terms and obligations."])

    # 1. Upload & Process
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(pdf_bytes), "deletable.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_res.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Verify pages exist
    pages_res = client.get(
        f"/api/documents/{doc_id}/pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pages_res.status_code == 200
    assert pages_res.get_json()["count"] == 1

    # 2. Delete document
    del_res = client.delete(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 200

    # 3. Subsequent page retrieval must return 404
    after_del_pages = client.get(
        f"/api/documents/{doc_id}/pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_del_pages.status_code == 404
    assert after_del_pages.get_json()["error"] == "not_found"

    # Processing trigger on deleted doc must return 404
    after_del_proc = client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_del_proc.status_code == 404


def test_processing_error_does_not_leak_internal_paths(
    client: FlaskClient,
) -> None:
    """Test that processing errors do not leak server filesystem paths."""
    _, token = create_user_and_token(client, "leakt@example.com", "Leak Tester")

    bad_pdf = b"%PDF-1.4\ncorrupt header and invalid stream object"
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(bad_pdf), "corrupt.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_res.get_json()["document"]["id"]

    proc_res = client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert proc_res.status_code in (400, 422, 500)
    data = proc_res.get_json()

    # Verify no absolute disk paths or stack traces leaked
    error_msg = data.get("message", "")
    assert "D:\\" not in error_msg
    assert "C:\\" not in error_msg
    assert "/home/" not in error_msg
    assert "Traceback" not in error_msg
