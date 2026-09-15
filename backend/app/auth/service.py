import re

from app.auth.models import User
from app.auth.password import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.auth.repository import UserRepository, get_user_repository
from app.auth.tokens import generate_token

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthError(Exception):
    """Base exception for authentication service errors."""

    pass


class ValidationError(AuthError):
    """Raised when input validation fails."""

    pass


class UserAlreadyExistsError(AuthError):
    """Raised when registering an email that is already registered."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when authentication credentials are invalid or incorrect."""

    pass


class UserInactiveError(AuthError):
    """Raised when an account is marked inactive."""

    pass


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format and length."""
    if not isinstance(email, str):
        return False, "Email must be a string."
    cleaned = email.strip()
    if not cleaned:
        return False, "Email cannot be empty."
    if len(cleaned) > 254:
        return False, "Email is too long."
    if not EMAIL_REGEX.match(cleaned):
        return False, "Invalid email address format."
    return True, ""


class AuthService:
    """Core authentication service orchestrating identity and tokens."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self._repository = repository or get_user_repository()

    def register(
        self,
        email: str,
        password: str,
        name: str,
        secret_key: str,
        token_expires_in: int = 3600,
    ) -> tuple[User, str]:
        """Register a new user account and return (user, token)."""
        # Validate email
        is_valid_email, email_error = validate_email(email)
        if not is_valid_email:
            raise ValidationError(email_error)

        # Validate password
        is_valid_pw, pw_error = validate_password_strength(password)
        if not is_valid_pw:
            raise ValidationError(pw_error)

        # Validate name
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Name is required and cannot be empty.")
        cleaned_name = name.strip()
        if len(cleaned_name) > 100:
            raise ValidationError("Name cannot exceed 100 characters.")

        normalized_email = email.strip().lower()

        # Check for existing email
        existing_user = self._repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email already exists.")

        # Hash password and create user
        pw_hash = hash_password(password)
        user = User(
            email=normalized_email,
            password_hash=pw_hash,
            name=cleaned_name,
        )
        saved_user = self._repository.save(user)

        # Generate token
        token = generate_token(
            user_id=saved_user.user_id,
            email=saved_user.email,
            secret_key=secret_key,
            expires_in_seconds=token_expires_in,
        )
        return saved_user, token

    def login(
        self,
        email: str,
        password: str,
        secret_key: str,
        token_expires_in: int = 3600,
    ) -> tuple[User, str]:
        """Authenticate user credentials and return (user, token)."""
        if not isinstance(email, str) or not email.strip():
            raise InvalidCredentialsError("Invalid email or password.")
        if not isinstance(password, str) or not password:
            raise InvalidCredentialsError("Invalid email or password.")

        normalized_email = email.strip().lower()
        user = self._repository.get_by_email(normalized_email)
        if user is None:
            # Generic error to prevent email enumeration
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise UserInactiveError("This account is inactive.")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        token = generate_token(
            user_id=user.user_id,
            email=user.email,
            secret_key=secret_key,
            expires_in_seconds=token_expires_in,
        )
        return user, token

    def get_user_by_id(self, user_id: str) -> User | None:
        """Retrieve user by ID."""
        return self._repository.get_by_id(user_id)
