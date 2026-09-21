import re

FORBIDDEN_LEGAL_PATTERNS = [
    r"\byou should sign\b",
    r"\byou should not sign\b",
    r"\byou must sign\b",
    r"\byou should sue\b",
    r"\byou must sue\b",
    r"\bthis is illegal\b",
    r"\bthis clause is illegal\b",
    r"\bthis provision is illegal\b",
    r"\bthis is unenforceable\b",
    r"\bthis is enforceable\b",
    r"\bthis clause is enforceable\b",
    r"\byou will win\b",
    r"\byou will lose\b",
    r"\byou have a strong case\b",
    r"\byou have no case\b",
    r"\bthe other party violated the law\b",
    r"\bthe employer violated the law\b",
    r"\bthe landlord violated the law\b",
]

MAX_BRIEF_TITLE_LENGTH = 255


def contains_forbidden_legal_claims(text: str) -> bool:
    """Check if text contains authoritative legal advice or outcome predictions."""
    if not text:
        return False
    text_lower = text.lower()
    return any(
        re.search(pat, text_lower) is not None for pat in FORBIDDEN_LEGAL_PATTERNS
    )


def sanitize_neutral_text(text: str) -> str:
    """Sanitize text by replacing forbidden advice assertions with neutral framing."""
    if not text:
        return text
    sanitized = text
    for pat in FORBIDDEN_LEGAL_PATTERNS:
        sanitized = re.sub(
            pat,
            "[Requires specific factual and jurisdiction-specific legal review]",
            sanitized,
            flags=re.IGNORECASE,
        )
    return sanitized


def validate_brief_title(title: str | None) -> str:
    """Validate and normalize a preparation brief title."""
    if not title or not title.strip():
        return "Lawyer-Preparation Brief"
    clean = title.strip()
    if len(clean) > MAX_BRIEF_TITLE_LENGTH:
        clean = clean[:MAX_BRIEF_TITLE_LENGTH].strip()
    return clean
