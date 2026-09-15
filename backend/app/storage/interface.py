from abc import ABC, abstractmethod


class StorageError(Exception):
    """Base exception for storage abstraction errors."""

    pass


class StorageSecurityError(StorageError):
    """Raised when an illegal storage key or path traversal attempt is detected."""

    pass


class StorageNotFoundError(StorageError):
    """Raised when a requested storage object is not found."""

    pass


class StorageService(ABC):
    """Abstract storage service interface."""

    @abstractmethod
    def save(self, storage_key: str, data: bytes) -> str:
        """Save binary data under the specified storage key and return the key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes | None:
        """Retrieve binary data by storage key, or None if not found."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete binary data by storage key. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if an object exists for the given storage key."""
        pass

    @abstractmethod
    def generate_storage_key(
        self, user_id: str, document_id: str, extension: str = ".pdf"
    ) -> str:
        """Generate a deterministic, secure, namespaced storage key."""
        pass
