from flask.testing import FlaskClient


def test_health_check_returns_200_and_ok_status(client: FlaskClient) -> None:
    """Test health endpoint returns 200, application/json, and expected payload."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "ok"
    assert data.get("service") == "claritykit-backend"
