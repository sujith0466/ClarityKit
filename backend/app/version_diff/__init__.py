"""Document Version Diff package (Phase 14)."""

from app.version_diff.diff_engine import VersionDiffEngine
from app.version_diff.models import (
    DocumentNotReadyForVersionDiffError,
    DocumentVersionDiff,
    InvalidVersionDiffInputError,
    VersionDiffCategory,
    VersionDiffClassification,
    VersionDiffError,
    VersionDiffFinding,
    VersionDiffNotFoundError,
    VersionDiffSummary,
    VersionDocumentRef,
    VersionEvidenceRef,
)
from app.version_diff.repository import (
    InMemoryVersionDiffRepository,
    PostgresVersionDiffRepository,
    VersionDiffRepository,
    in_memory_version_diff_repository,
)
from app.version_diff.service import VersionDiffService
from app.version_diff.validation import VersionDiffValidator

__all__ = [
    "VersionDiffClassification",
    "VersionDiffCategory",
    "VersionEvidenceRef",
    "VersionDiffFinding",
    "VersionDocumentRef",
    "VersionDiffSummary",
    "DocumentVersionDiff",
    "VersionDiffError",
    "VersionDiffNotFoundError",
    "InvalidVersionDiffInputError",
    "DocumentNotReadyForVersionDiffError",
    "VersionDiffValidator",
    "VersionDiffEngine",
    "VersionDiffRepository",
    "InMemoryVersionDiffRepository",
    "PostgresVersionDiffRepository",
    "in_memory_version_diff_repository",
    "VersionDiffService",
]
