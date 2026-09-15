from collections.abc import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.config import TestingConfig


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create and configure a testing application instance."""
    app = create_app(TestingConfig)
    yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the application."""
    return app.test_client()
