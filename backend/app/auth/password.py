import re

from werkzeug.security import check_password_hash, generate_password_hash

# Minimum password length
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    """Hash a plaintext password using a strong cryptographic hash."""
    return generate_password_hash(password, method="scrypt")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored cryptographic hash."""
    if not plain_password or not hashed_password:
        return False
    return check_password_hash(hashed_password, plain_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate that the password satisfies minimum security requirements."""
    if not isinstance(password, str):
        return False, "Password must be a string."

    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            False,
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.",
        )

    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."

    return True, ""
