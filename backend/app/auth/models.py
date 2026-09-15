import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class User:
    """Core user entity for authentication and resource ownership."""

    email: str
    password_hash: str
    name: str
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return safe, sanitized dictionary representation without password hash."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
