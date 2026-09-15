import os


def parse_allowed_origins(raw_origins: str | None = None) -> list[str]:
    """Parse a comma-separated string of allowed CORS origins."""
    if raw_origins is None:
        raw_origins = os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


class Config:
    """Base application configuration loaded from environment variables."""

    ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    TESTING: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Restrictive CORS: explicit origins only
    ALLOWED_ORIGINS: list[str] = parse_allowed_origins()


class DevelopmentConfig(Config):
    """Development environment configuration."""

    ENV: str = "development"
    DEBUG: bool = True


class TestingConfig(Config):
    """Testing environment configuration."""

    ENV: str = "testing"
    TESTING: bool = True
    DEBUG: bool = True
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


class ProductionConfig(Config):
    """Production environment configuration with strict safety checks."""

    ENV: str = "production"
    DEBUG: bool = False
