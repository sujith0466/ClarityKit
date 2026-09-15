import os
from unittest.mock import patch

from app.config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    parse_allowed_origins,
)


def test_default_config_values() -> None:
    """Test default values of the base Config class."""
    config = Config()
    assert config.TESTING is False
    assert isinstance(config.ALLOWED_ORIGINS, list)
    assert len(config.ALLOWED_ORIGINS) > 0
    assert config.SECRET_KEY is not None


def test_development_config_values() -> None:
    """Test values for DevelopmentConfig."""
    config = DevelopmentConfig()
    assert config.ENV == "development"
    assert config.DEBUG is True
    assert config.TESTING is False


def test_testing_config_values() -> None:
    """Test values for TestingConfig."""
    config = TestingConfig()
    assert config.ENV == "testing"
    assert config.TESTING is True
    assert config.DEBUG is True
    assert "http://localhost:5173" in config.ALLOWED_ORIGINS


def test_production_config_values() -> None:
    """Test values for ProductionConfig."""
    config = ProductionConfig()
    assert config.ENV == "production"
    assert config.DEBUG is False
    assert config.TESTING is False


def test_parse_allowed_origins_custom() -> None:
    """Test parse_allowed_origins with custom comma-separated list."""
    origins = parse_allowed_origins(
        "https://claritykit.app, https://app.claritykit.io "
    )
    assert origins == ["https://claritykit.app", "https://app.claritykit.io"]


def test_parse_allowed_origins_env_override() -> None:
    """Test parse_allowed_origins reads from environment if not supplied."""
    with patch.dict(
        os.environ,
        {"ALLOWED_ORIGINS": "https://custom.origin.com, http://localhost:3000"},
    ):
        origins = parse_allowed_origins()
        assert origins == ["https://custom.origin.com", "http://localhost:3000"]
