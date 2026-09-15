from flask.testing import FlaskClient

from app.auth.repository import get_user_repository
from app.auth.tokens import generate_token


def setup_function() -> None:
    """Clear repository before each test."""
    get_user_repository().clear()


def test_register_success(client: FlaskClient) -> None:
    """Test successful user registration returns 201 and token."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "counsel@example.com",
            "password": "SecurePassword123",
            "name": "Legal Counsel",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "success"
    assert "token" in data
    user = data.get("user", {})
    assert user.get("email") == "counsel@example.com"
    assert user.get("name") == "Legal Counsel"
    assert "user_id" in user
    # Critical security check: password_hash must never be returned!
    assert "password_hash" not in user
    assert "password" not in user


def test_register_duplicate_email(client: FlaskClient) -> None:
    """Test that registering an existing email returns 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123",
        "name": "User One",
    }
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 409
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "conflict"


def test_register_invalid_email(client: FlaskClient) -> None:
    """Test that registering with invalid email format returns 400."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePassword123",
            "name": "Invalid User",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "validation_error"


def test_register_weak_password(client: FlaskClient) -> None:
    """Test that registering with weak password returns 400."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "name": "Weak User",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "validation_error"


def test_login_success(client: FlaskClient) -> None:
    """Test successful login returns 200 and token."""
    client.post(
        "/api/auth/register",
        json={
            "email": "lawyer@example.com",
            "password": "StrongPassword123",
            "name": "Senior Lawyer",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "lawyer@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "success"
    assert "token" in data
    user = data.get("user", {})
    assert user.get("email") == "lawyer@example.com"
    assert "password_hash" not in user


def test_login_invalid_password(client: FlaskClient) -> None:
    """Test login with wrong password returns 401 with generic error."""
    client.post(
        "/api/auth/register",
        json={
            "email": "lawyer2@example.com",
            "password": "StrongPassword123",
            "name": "Lawyer Two",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "lawyer2@example.com",
            "password": "WrongPassword999",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "unauthorized"


def test_login_nonexistent_email(client: FlaskClient) -> None:
    """Test login with non-existent email returns 401 with generic message."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "ghost@example.com",
            "password": "SomePassword123",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "unauthorized"


def test_logout(client: FlaskClient) -> None:
    """Test logout endpoint returns 200."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "success"


def test_me_authenticated(client: FlaskClient) -> None:
    """Test /api/auth/me returns current user info with valid token."""
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "email": "attorney@example.com",
            "password": "Password123",
            "name": "Attorney At Law",
        },
    )
    token = reg_resp.get_json()["token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    user = data.get("user", {})
    assert user.get("email") == "attorney@example.com"
    assert "password_hash" not in user


def test_me_unauthenticated(client: FlaskClient) -> None:
    """Test /api/auth/me returns 401 when no token is provided."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "unauthorized"


def test_me_malformed_token(client: FlaskClient) -> None:
    """Test /api/auth/me returns 401 when invalid token format is passed."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "unauthorized"


def test_me_expired_token(client: FlaskClient) -> None:
    """Test /api/auth/me returns 401 when token has expired."""
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "email": "expired@example.com",
            "password": "Password123",
            "name": "Expired User",
        },
    )
    user_id = reg_resp.get_json()["user"]["user_id"]

    # Generate token with negative expiration
    expired_token = generate_token(
        user_id=user_id,
        email="expired@example.com",
        secret_key="dev-secret-key-change-in-production",
        expires_in_seconds=-10,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "token_expired"
