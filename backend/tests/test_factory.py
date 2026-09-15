from app import create_app
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig


def test_create_app_testing() -> None:
    """Test application factory with TestingConfig."""
    app = create_app(TestingConfig)
    assert app.testing is True
    assert app.config["ENV"] == "testing"


def test_create_app_development() -> None:
    """Test application factory with DevelopmentConfig."""
    app = create_app(DevelopmentConfig)
    assert app.testing is False
    assert app.config["ENV"] == "development"
    assert app.config["DEBUG"] is True


def test_create_app_production() -> None:
    """Test application factory with ProductionConfig."""
    app = create_app(ProductionConfig)
    assert app.testing is False
    assert app.config["ENV"] == "production"
    assert app.config["DEBUG"] is False
