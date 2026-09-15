import hashlib
import os
import re
from typing import Any

# Security constants
PDF_MAGIC_BYTES = b"%PDF-"
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
}
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Dangerous characters and Windows reserved names
CONTROL_CHARS_REGEX = re.compile(r"[\x00-\x1f\x7f-\x9f]")
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


class FileValidationError(Exception):
    """Base exception for document file validation errors."""

    pass


class MissingFileError(FileValidationError):
    """Raised when no file is present in the upload request."""

    pass


class EmptyFileError(FileValidationError):
    """Raised when the uploaded file contains 0 bytes."""

    pass


class FileTooLargeError(FileValidationError):
    """Raised when the uploaded file exceeds the configured size limit."""

    pass


class InvalidFileTypeError(FileValidationError):
    """Raised when file extension, MIME, or magic bytes are invalid."""

    pass


def sanitize_filename(filename: str | None) -> str:
    """Sanitize original filename to prevent path traversal and shell injection.

    Replaces path separators, strips directory parts, eliminates control
    characters and null bytes, and ensures a safe fallback name.
    """
    if not filename or not isinstance(filename, str):
        return "document.pdf"

    # Strip null bytes and control chars
    clean = CONTROL_CHARS_REGEX.sub("", filename)

    # Extract basename to strip absolute and relative path traversals (Unix & Windows)
    clean = clean.replace("\\", "/")
    clean = os.path.basename(clean).strip()

    # Remove any leading dots or slashes
    clean = clean.lstrip("./\\")

    # Replace suspicious characters
    clean = re.sub(r"[^a-zA-Z0-9._\- ]", "_", clean).strip()

    # Check for empty string or Windows reserved device names
    name_without_ext = os.path.splitext(clean)[0].upper()
    if not clean or name_without_ext in RESERVED_NAMES:
        return "document.pdf"

    # Enforce maximum filename length (255 characters)
    if len(clean) > 255:
        base, ext = os.path.splitext(clean)
        clean = base[: 255 - len(ext)] + ext

    return clean


def validate_file_upload(
    file_obj: Any,
    max_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES,
) -> tuple[bytes, str, str, str]:
    """Validate uploaded file for presence, size, filename, and PDF signature.

    Returns:
        tuple of (content_bytes, sanitized_filename, content_type, sha256_hash)
    """
    if file_obj is None:
        raise MissingFileError("No file was uploaded.")

    # Validate filename
    raw_filename = getattr(file_obj, "filename", "")
    if not raw_filename or not raw_filename.strip():
        raise MissingFileError("Uploaded file must have a filename.")

    sanitized_name = sanitize_filename(raw_filename)
    _, ext = os.path.splitext(sanitized_name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"Unsupported file extension '{ext}'. Only PDF files are supported."
        )

    # Read content safely
    try:
        if hasattr(file_obj, "read"):
            content: bytes = file_obj.read()
        else:
            raise FileValidationError("Invalid file object provided.")
    except Exception as e:
        raise FileValidationError(f"Failed to read upload stream: {e}") from e

    # Size check
    file_size = len(content)
    if file_size == 0:
        raise EmptyFileError("The uploaded file is empty (0 bytes).")

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise FileTooLargeError(
            f"File size exceeds maximum allowed limit of {max_mb:.1f} MB."
        )

    # Content signature / Magic bytes check
    if not content.startswith(PDF_MAGIC_BYTES):
        raise InvalidFileTypeError(
            "Invalid file content. The file does not contain a valid PDF signature."
        )

    # Compute SHA-256 hash
    content_hash = hashlib.sha256(content).hexdigest()

    return content, sanitized_name, "application/pdf", content_hash
