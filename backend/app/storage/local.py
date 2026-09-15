import os
import re

from app.storage.interface import (
    StorageError,
    StorageSecurityError,
    StorageService,
)


class LocalStorageService(StorageService):
    """Secure local filesystem storage adapter with path containment enforcement."""

    def __init__(self, root_dir: str | None = None) -> None:
        if root_dir is None:
            # Default to data/uploads relative to backend root
            root_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
            )
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> str:
        """Resolve storage key to an absolute filesystem path.

        Enforces strict root containment.
        """
        if not storage_key or not isinstance(storage_key, str):
            raise StorageSecurityError("Storage key must be a non-empty string.")

        if "\x00" in storage_key:
            raise StorageSecurityError("Null bytes in storage key are prohibited.")

        # Normalize forward/backward slashes
        normalized_key = storage_key.replace("\\", "/").lstrip("/")

        # Prevent empty or root keys
        if not normalized_key:
            raise StorageSecurityError("Storage key cannot be root.")

        # Resolve canonical absolute target path
        target_path = os.path.abspath(os.path.join(self.root_dir, normalized_key))

        # Containment check: target must be inside root_dir
        canonical_root = self.root_dir
        if (
            not target_path.startswith(canonical_root + os.sep)
            and target_path != canonical_root
        ):
            raise StorageSecurityError(
                f"Path traversal detected: '{storage_key}' escapes storage root."
            )

        return target_path

    def save(self, storage_key: str, data: bytes) -> str:
        """Save binary data to a secure namespaced path."""
        target_path = self._resolve_safe_path(storage_key)
        try:
            parent_dir = os.path.dirname(target_path)
            os.makedirs(parent_dir, exist_ok=True)

            with open(target_path, "wb") as f:
                f.write(data)
            return storage_key
        except Exception as e:
            raise StorageError(f"Failed to write file to storage: {e}") from e

    def get(self, storage_key: str) -> bytes | None:
        """Retrieve binary content for a given storage key."""
        target_path = self._resolve_safe_path(storage_key)
        if not os.path.isfile(target_path):
            return None
        try:
            with open(target_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read file from storage: {e}") from e

    def delete(self, storage_key: str) -> bool:
        """Safely delete stored file."""
        target_path = self._resolve_safe_path(storage_key)
        if not os.path.isfile(target_path):
            return False
        try:
            os.remove(target_path)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete file from storage: {e}") from e

    def exists(self, storage_key: str) -> bool:
        """Check if file exists at target storage path."""
        target_path = self._resolve_safe_path(storage_key)
        return os.path.isfile(target_path)

    def generate_storage_key(
        self, user_id: str, document_id: str, extension: str = ".pdf"
    ) -> str:
        """Generate a safe, namespaced storage key."""
        clean_user = re.sub(r"[^a-zA-Z0-9_-]", "", user_id)
        clean_doc = re.sub(r"[^a-zA-Z0-9_-]", "", document_id)
        clean_ext = ".pdf" if extension.lower() == ".pdf" else ".bin"
        return f"users/{clean_user}/documents/{clean_doc}{clean_ext}"


# Default singleton storage service instance
default_storage_service: StorageService = LocalStorageService()
_default_storage_service: StorageService = default_storage_service


def get_storage_service() -> StorageService:
    """Get active storage service instance."""
    return _default_storage_service


def set_storage_service(service: StorageService) -> None:
    """Set active storage service instance (for testing/customization)."""
    global _default_storage_service
    _default_storage_service = service
