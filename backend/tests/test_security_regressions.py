import jwt
from flask.testing import FlaskClient

from app.auth.repository import get_user_repository
from app.auth.tokens import generate_token


def setup_function() -> None:
    """Reset user repository."""
    get_user_repository().clear()


def test_password_hash_never_leaked_in_registration_response(
    client: FlaskClient,
) -> None:
    """Security Regression: Registration response must never contain password hash."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "privacy@example.com",
            "password": "SuperSecretPassword123",
            "name": "Privacy Advocate",
        },
    )
    assert response.status_code == 201
    text = response.get_data(as_text=True)
    assert "scrypt:" not in text
    assert "pbkdf2:" not in text
    assert "SuperSecretPassword123" not in text


def test_password_hash_never_leaked_in_login_response(
    client: FlaskClient,
) -> None:
    """Security Regression: Login response must never contain password hash."""
    client.post(
        "/api/auth/register",
        json={
            "email": "privacy2@example.com",
            "password": "SuperSecretPassword123",
            "name": "Privacy Advocate 2",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={
            "email": "privacy2@example.com",
            "password": "SuperSecretPassword123",
        },
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "scrypt:" not in text
    assert "pbkdf2:" not in text


def test_forged_jwt_signature_is_rejected(client: FlaskClient) -> None:
    """Security Regression: Token signed with wrong secret key is rejected with 401."""
    client.post(
        "/api/auth/register",
        json={
            "email": "target@example.com",
            "password": "Password123",
            "name": "Target User",
        },
    )

    # Attacker crafts token signed with 'attacker-secret'
    forged_token = generate_token(
        user_id="any-id",
        email="target@example.com",
        secret_key="attacker-wrong-secret",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data.get("error") == "unauthorized"


def test_none_algorithm_jwt_is_rejected(client: FlaskClient) -> None:
    """Security Regression: Token with algorithm 'none' is rejected."""
    payload = {"sub": "fake-user", "email": "fake@example.com"}
    unsigned_token = f"{jwt.encode(payload, '', algorithm='none')}"

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {unsigned_token}"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data.get("error") == "unauthorized"


def test_stack_traces_are_never_exposed_on_server_errors(
    client: FlaskClient,
) -> None:
    """Security Regression: Error responses must not include Python tracebacks."""
    response = client.post(
        "/api/auth/register",
        data="invalid non-json raw string",
        content_type="application/json",
    )
    assert response.status_code in (400, 500)
    data = response.get_json()
    assert data is not None
    assert "Traceback" not in str(data)
    assert "File " not in str(data)
    assert "TypeError" not in str(data)
    assert "ValueError" not in str(data)
