from flask.testing import FlaskClient


def test_404_not_found_returns_json(client: FlaskClient) -> None:
    """Test that requesting an undefined endpoint returns structured JSON 404."""
    response = client.get("/api/nonexistent-route")
    assert response.status_code == 404
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "not_found"
    assert "not found" in data.get("message", "").lower()


def test_405_method_not_allowed_returns_json(client: FlaskClient) -> None:
    """Test that requesting an endpoint with unsupported method returns JSON 405."""
    response = client.post("/api/health")
    assert response.status_code == 405
    data = response.get_json()
    assert data is not None
    assert data.get("error") == "method_not_allowed"
    assert "method not allowed" in data.get("message", "").lower()
