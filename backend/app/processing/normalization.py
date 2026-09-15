import re

# Control characters to strip: all 0x00-0x1F and 0x7F-0x9F,
# except \t (0x09) and \n (0x0A)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Multiple blank lines collapse pattern (3 or more newlines reduced to 2 newlines)
EXCESSIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")


def normalize_extracted_text(text: str | None) -> str:
    """Perform conservative, deterministic normalization on extracted text.

    Preserves legal phrasing, numbers, dates, indentation structure, and
    case while stripping null bytes, invalid control characters, and
    normalizing line endings.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # 1. Normalize line breaks to Unix LF (\n)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip non-printable and invalid control characters (preserving \n and \t)
    normalized = CONTROL_CHARS_PATTERN.sub("", normalized)

    # 3. Collapse 3+ consecutive newlines to maximum 2 newlines (paragraph boundary)
    normalized = EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", normalized)

    # 4. Strip surrounding whitespace on the page level
    return normalized.strip()
