import os
import re


def parse_allowed_origins(raw_origins: str | None = None) -> list[str]:
    """Parse a comma-separated string of allowed CORS origins."""
    if raw_origins is None:
        raw_origins = os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def normalize_database_url(url: str | None) -> str | None:
    """Normalize database connection URL (e.g. converting postgres:// to postgresql://)."""
    if not url or not url.strip():
        return None
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql://" + trimmed[len("postgres://") :]
    return trimmed


def mask_database_url(url: str | None) -> str:
    """Return a masked representation of a database URL for safe logging/reporting."""
    if not url:
        return "NOT_CONFIGURED"
    # Mask password in URL scheme://user:password@host:port/dbname
    pattern = r"://([^:]+):([^@]+)@"
    return re.sub(pattern, r"://\1:***@", url)


class Config:
    """Base application configuration loaded from environment variables."""

    ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    TESTING: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Authentication & JWT Configuration
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_SECONDS: int = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))

    # Database Configuration (Neon PostgreSQL / pgvector)
    DATABASE_URL: str | None = normalize_database_url(os.getenv("DATABASE_URL"))

    # Storage & Upload Configuration
    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "data/documents")
    MAX_UPLOAD_SIZE_BYTES: int = int(
        os.getenv("MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024))
    )

    # Processing & OCR Configuration
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "mock")

    # Embedding & Retrieval Configuration
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "deterministic")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "deterministic-minilm-384")

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
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_EXPIRATION_SECONDS: int = 3600
    DATABASE_URL: str | None = None


class ProductionConfig(Config):
    """Production environment configuration with strict safety checks."""

    ENV: str = "production"
    DEBUG: bool = False
