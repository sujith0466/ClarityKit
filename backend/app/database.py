import logging
from pathlib import Path

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extensions import connection

from app.config import Config, mask_database_url

logger = logging.getLogger(__name__)


def get_db_connection(database_url: str | None = None) -> connection:
    """Create a new PostgreSQL database connection and register pgvector."""
    url = database_url or Config.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL is not configured.")

    try:
        conn = psycopg2.connect(url)
        # Register pgvector extension types with connection
        try:
            register_vector(conn)
        except Exception as e:
            logger.warning(
                "Could not register pgvector on connection: %s",
                e,
            )
        return conn
    except Exception as e:
        logger.error(
            "Failed to connect to database (%s): %s",
            mask_database_url(url),
            e,
        )
        raise


def run_migrations(database_url: str | None = None) -> list[str]:
    """Execute all pending SQL migrations against the target database."""
    url = database_url or Config.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL is not configured.")

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found at {migrations_dir}")

    migration_files = sorted(migrations_dir.glob("*.sql"))
    applied: list[str] = []

    conn = psycopg2.connect(url)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Create migrations tracking table if not exists
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            # Check already applied migrations
            cur.execute("SELECT version FROM schema_migrations;")
            already_applied = {row[0] for row in cur.fetchall()}

            for migration_file in migration_files:
                version = migration_file.name
                if version in already_applied:
                    continue

                logger.info("Applying migration: %s", version)
                sql_content = migration_file.read_text(encoding="utf-8-sig")
                cur.execute(sql_content)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s);",
                    (version,),
                )
                applied.append(version)

        # After applying migrations, register pgvector
        try:
            register_vector(conn)
        except Exception:
            pass

    finally:
        conn.close()

    return applied
