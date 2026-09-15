import threading
from abc import ABC, abstractmethod

from app.auth.models import User


class UserRepository(ABC):
    """Abstract user repository interface."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save a new user or update an existing user."""
        pass

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by their unique user_id."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by their lowercase email."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored users (primarily for testing)."""
        pass


class InMemoryUserRepository(UserRepository):
    """Thread-safe in-memory user repository for Phase 2."""

    def __init__(self) -> None:
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._lock = threading.RLock()

    def save(self, user: User) -> User:
        with self._lock:
            self._users_by_id[user.user_id] = user
            self._users_by_email[user.email.lower()] = user
            return user

    def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            return self._users_by_email.get(email.lower().strip())

    def clear(self) -> None:
        with self._lock:
            self._users_by_id.clear()
            self._users_by_email.clear()


# Default singleton repository instance
_default_repository: UserRepository = InMemoryUserRepository()


def get_user_repository() -> UserRepository:
    """Get the active user repository instance."""
    return _default_repository


def set_user_repository(repository: UserRepository) -> None:
    """Set the active user repository instance (for testing/customization)."""
    global _default_repository
    _default_repository = repository
