from dataclasses import dataclass
from typing import Any

import pytest
from flask import Flask, Response, g, jsonify
from flask.testing import FlaskClient

from app.auth.context import require_auth, require_ownership
from app.auth.models import User
from app.auth.repository import get_user_repository
from app.auth.tokens import generate_token


@dataclass
class MockDocumentResource:
    """Mock resource to test authorization and IDOR protection."""

    resource_id: str
    user_id: str
    title: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "title": self.title,
        }


# In-memory resource store for testing
_test_resources: dict[str, MockDocumentResource] = {}


def load_test_resource(resource_id: str) -> MockDocumentResource | None:
    """Resource loader function for @require_ownership."""
    return _test_resources.get(resource_id)


@pytest.fixture
def auth_app(app: Flask) -> Flask:
    """Register test resource routes on the application."""
    if "get_resource" not in app.view_functions:

        @app.route("/api/test-resources/<resource_id>", methods=["GET"])
        @require_ownership(load_test_resource, id_param_name="resource_id")
        def get_resource(resource_id: str) -> tuple[Response, int]:
            resource: MockDocumentResource = g.current_resource
            return jsonify({"status": "success", "data": resource.to_dict()}), 200

        @app.route("/api/test-resources/<resource_id>", methods=["PUT"])
        @require_ownership(load_test_resource, id_param_name="resource_id")
        def update_resource(resource_id: str) -> tuple[Response, int]:
            # Server-side derived owner, ignores body modifications
            resource: MockDocumentResource = g.current_resource
            return jsonify({"status": "updated", "data": resource.to_dict()}), 200

        @app.route("/api/test-resources/protected-general", methods=["GET"])
        @require_auth
        def protected_general() -> tuple[Response, int]:
            user: User = g.current_user
            return jsonify({"status": "success", "user_id": user.user_id}), 200

    return app


@pytest.fixture(autouse=True)
def setup_auth_test_data() -> None:
    """Seed test users and resources."""
    user_repo = get_user_repository()
    user_repo.clear()
    _test_resources.clear()

    # User A
    user_a = User(
        user_id="user-a-1111",
        email="usera@example.com",
        password_hash="hash_a",
        name="User Alpha",
    )
    user_repo.save(user_a)

    # User B
    user_b = User(
        user_id="user-b-2222",
        email="userb@example.com",
        password_hash="hash_b",
        name="User Beta",
    )
    user_repo.save(user_b)

    # Resources
    _test_resources["doc-a-1"] = MockDocumentResource(
        resource_id="doc-a-1",
        user_id="user-a-1111",
        title="User A Private Contract",
    )
    _test_resources["doc-b-1"] = MockDocumentResource(
        resource_id="doc-b-1",
        user_id="user-b-2222",
        title="User B Sensitive NDA",
    )


def test_unauthenticated_protected_route_returns_401(
    auth_app: Flask, client: FlaskClient
) -> None:
    """Test unauthenticated access to general protected route returns 401."""
    response = client.get("/api/test-resources/protected-general")
    assert response.status_code == 401
    data = response.get_json()
    assert data.get("error") == "unauthorized"


def test_user_a_can_access_own_resource(auth_app: Flask, client: FlaskClient) -> None:
    """Test User A can access resource owned by User A."""
    token = generate_token(
        user_id="user-a-1111",
        email="usera@example.com",
        secret_key="dev-secret-key-change-in-production",
    )

    response = client.get(
        "/api/test-resources/doc-a-1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data.get("status") == "success"
    assert data["data"]["title"] == "User A Private Contract"


def test_idor_protection_user_a_accessing_user_b_resource_returns_404(
    auth_app: Flask, client: FlaskClient
) -> None:
    """CRITICAL IDOR: User A requesting User B's resource returns 404, NOT 403."""
    token = generate_token(
        user_id="user-a-1111",
        email="usera@example.com",
        secret_key="dev-secret-key-change-in-production",
    )

    # User A requests User B's resource 'doc-b-1'
    response = client.get(
        "/api/test-resources/doc-b-1",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Must be 404 Not Found so existence is never leaked
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "not_found"
    assert "not found" in data.get("message", "").lower()


def test_idor_protection_user_b_accessing_user_a_resource_returns_404(
    auth_app: Flask, client: FlaskClient
) -> None:
    """CRITICAL IDOR: User B requesting User A's resource must return 404."""
    token = generate_token(
        user_id="user-b-2222",
        email="userb@example.com",
        secret_key="dev-secret-key-change-in-production",
    )

    # User B requests User A's resource 'doc-a-1'
    response = client.get(
        "/api/test-resources/doc-a-1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "not_found"


def test_accessing_nonexistent_resource_returns_404(
    auth_app: Flask, client: FlaskClient
) -> None:
    """Test authenticated user requesting nonexistent resource returns 404."""
    token = generate_token(
        user_id="user-a-1111",
        email="usera@example.com",
        secret_key="dev-secret-key-change-in-production",
    )

    response = client.get(
        "/api/test-resources/nonexistent-uuid-999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "not_found"


def test_unauthenticated_access_to_resource_returns_401(
    auth_app: Flask, client: FlaskClient
) -> None:
    """Test unauthenticated access to resource endpoint returns 401."""
    response = client.get("/api/test-resources/doc-a-1")
    assert response.status_code == 401
    data = response.get_json()
    assert data.get("error") == "unauthorized"


def test_id_substitution_attack_in_body_is_ignored(
    auth_app: Flask, client: FlaskClient
) -> None:
    """Test that injecting owner_id in body cannot bypass ownership."""
    token = generate_token(
        user_id="user-a-1111",
        email="usera@example.com",
        secret_key="dev-secret-key-change-in-production",
    )

    # User A tries to update User B's resource by injecting owner_id
    response = client.put(
        "/api/test-resources/doc-b-1",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "user-a-1111", "title": "Hacked Title"},
    )

    # Must still return 404 Not Found
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "not_found"
