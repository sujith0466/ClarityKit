from app.qa.models import InvalidQuestionError

MAX_QUESTION_LENGTH = 2000
MAX_TITLE_LENGTH = 255


def validate_question_text(
    question: str | None, max_length: int = MAX_QUESTION_LENGTH
) -> str:
    """Validate and sanitize a user-submitted question.

    Rejects empty, whitespace-only, or oversized questions.
    """
    if question is None:
        raise InvalidQuestionError("Question cannot be empty.")

    clean_question = question.strip()
    if not clean_question:
        raise InvalidQuestionError("Question cannot be empty or whitespace only.")

    if len(clean_question) > max_length:
        raise InvalidQuestionError(
            f"Question length ({len(clean_question)} characters) exceeds maximum "
            f"limit of {max_length} characters."
        )

    return clean_question


def validate_session_title(
    title: str | None, max_length: int = MAX_TITLE_LENGTH
) -> str:
    """Validate and sanitize a session title."""
    if not title or not title.strip():
        return "Document Q&A Session"

    clean_title = title.strip()
    if len(clean_title) > max_length:
        return clean_title[:max_length]
    return clean_title
