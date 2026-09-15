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


def test_unauthenticated_retrieval_endpoints_rejected(
    client: FlaskClient,
) -> None:
    """Test that all Phase 5 retrieval endpoints strictly require auth (401)."""
    fake_doc_id = "doc-unauth-123"

    res_index = client.post(f"/api/documents/{fake_doc_id}/index")
    assert res_index.status_code == 401
    assert res_index.get_json()["error"] == "unauthorized"

    res_chunks = client.get(f"/api/documents/{fake_doc_id}/chunks")
    assert res_chunks.status_code == 401
    assert res_chunks.get_json()["error"] == "unauthorized"

    res_summary = client.get(f"/api/documents/{fake_doc_id}/index")
    assert res_summary.status_code == 401
    assert res_summary.get_json()["error"] == "unauthorized"

    res_search = client.post(
        "/api/retrieval/search",
        json={"query": "test query"},
    )
    assert res_search.status_code == 401
    assert res_search.get_json()["error"] == "unauthorized"


def test_adversarial_cross_tenant_search_isolation(
    client: FlaskClient,
) -> None:
    """Test that User A search NEVER returns User B's chunk."""
    user_a_id, token_a = create_user_and_token(
        client, "alice_ret@example.com", "Alice A"
    )
    user_b_id, token_b = create_user_and_token(client, "bob_ret@example.com", "Bob B")

    # Alice uploads and indexes a lease document
    alice_pdf = create_synthetic_pdf(
        ["Alice residential tenancy lease agreement terms for unit 4B."]
    )
    alice_upload = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"file": (io.BytesIO(alice_pdf), "alice_lease.pdf")},
        content_type="multipart/form-data",
    )
    alice_doc_id = alice_upload.get_json()["document"]["id"]
    client.post(
        f"/api/documents/{alice_doc_id}/process",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    client.post(
        f"/api/documents/{alice_doc_id}/index",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Bob uploads and indexes a highly specific patent license document
    bob_pdf = create_synthetic_pdf(
        ["Bob Quantum Cryptography Patent License and Royalty Agreement 98765."]
    )
    bob_upload = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"file": (io.BytesIO(bob_pdf), "bob_patent.pdf")},
        content_type="multipart/form-data",
    )
    bob_doc_id = bob_upload.get_json()["document"]["id"]
    client.post(
        f"/api/documents/{bob_doc_id}/process",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    client.post(
        f"/api/documents/{bob_doc_id}/index",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # Alice searches for Bob's exact phrase "Quantum Cryptography Patent Royalty"
    alice_search_res = client.post(
        "/api/retrieval/search",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "query": "Quantum Cryptography Patent License Royalty Agreement 98765",
            "top_k": 5,
        },
    )
    assert alice_search_res.status_code == 200
    alice_search_data = alice_search_res.get_json()

    # User A's results MUST NOT contain Bob's document or text
    for result in alice_search_data["results"]:
        assert result["document_id"] != bob_doc_id
        assert "Quantum Cryptography" not in result["text"]


def test_cross_tenant_idor_index_and_chunks_returns_404(
    client: FlaskClient,
) -> None:
    """Test that User B cannot index or retrieve chunks of User A's document (404)."""
    _, token_a = create_user_and_token(client, "alice_idor@example.com", "Alice IDOR")
    _, token_b = create_user_and_token(client, "bob_idor@example.com", "Bob IDOR")

    alice_pdf = create_synthetic_pdf(["Alice sensitive employment contract."])
    alice_upload = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"file": (io.BytesIO(alice_pdf), "alice_contract.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = alice_upload.get_json()["document"]["id"]
    client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    client.post(
        f"/api/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Bob attempts to index Alice's document -> 404
    bob_index_res = client.post(
        f"/api/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert bob_index_res.status_code == 404
    assert bob_index_res.get_json()["error"] == "not_found"

    # Bob attempts to get chunks of Alice's document -> 404
    bob_chunks_res = client.get(
        f"/api/documents/{doc_id}/chunks",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert bob_chunks_res.status_code == 404
    assert bob_chunks_res.get_json()["error"] == "not_found"

    # Bob attempts to search with document_id scoped to Alice's doc -> 404
    bob_search_res = client.post(
        "/api/retrieval/search",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "query": "employment contract",
            "document_id": doc_id,
        },
    )
    assert bob_search_res.status_code == 404
    assert bob_search_res.get_json()["error"] == "not_found"


def test_document_deletion_cascades_to_chunks(
    client: FlaskClient,
) -> None:
    """Test that deleting a document cascades to remove chunks from vector retrieval."""
    _, token = create_user_and_token(client, "deleter_ret@example.com", "Deleter Ret")

    pdf = create_synthetic_pdf(["Unique term: AlphaBetaGammaXYZ Agreement."])
    upload_res = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"file": (io.BytesIO(pdf), "deletable_search.pdf")},
        content_type="multipart/form-data",
    )
    doc_id = upload_res.get_json()["document"]["id"]
    client.post(
        f"/api/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/api/documents/{doc_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Verify search returns chunk before deletion
    search_before = client.post(
        "/api/retrieval/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "AlphaBetaGammaXYZ"},
    )
    assert search_before.status_code == 200
    assert search_before.get_json()["count"] >= 1

    # Delete document
    del_res = client.delete(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 200

    # Search after deletion must return 0 results
    search_after = client.post(
        "/api/retrieval/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "AlphaBetaGammaXYZ"},
    )
    assert search_after.status_code == 200
    assert search_after.get_json()["count"] == 0
