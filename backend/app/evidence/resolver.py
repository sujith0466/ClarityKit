import logging
import re
import unicodedata
from typing import NamedTuple

from app.evidence.models import (
    EvidenceMatchType,
    EvidenceValidationStatus,
)

logger = logging.getLogger(__name__)


class ResolutionResult(NamedTuple):
    status: EvidenceValidationStatus
    match_type: EvidenceMatchType
    char_start: int | None
    char_end: int | None
    source_text: str | None
    reason: str | None


class SourceSpanResolver:
    """High-performance mechanical source span resolver with strict validation."""

    MAX_PAGE_RANGE = 10

    @staticmethod
    def _normalize_whitespace_keep_tokens(
        text: str,
    ) -> tuple[str, list[tuple[int, int]]]:
        """Normalize Unicode spaces and line breaks while tracking original offsets."""
        cleaned_chars: list[str] = []
        char_index_map: list[int] = []

        for idx, ch in enumerate(text):
            if ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
                continue
            if unicodedata.category(ch) == "Zs":
                cleaned_chars.append(" ")
            else:
                cleaned_chars.append(ch)
            char_index_map.append(idx)

        cleaned_text = "".join(cleaned_chars)

        tokens: list[str] = []
        token_ranges: list[tuple[int, int]] = []

        for m in re.finditer(r"\S+", cleaned_text):
            tokens.append(m.group())
            start_in_cleaned = m.start()
            end_in_cleaned = m.end() - 1

            orig_start = char_index_map[start_in_cleaned]
            orig_end = char_index_map[end_in_cleaned] + 1
            token_ranges.append((orig_start, orig_end))

        normalized = " ".join(tokens)
        return normalized, token_ranges

    @classmethod
    def resolve_single_page(cls, page_text: str, source_span: str) -> ResolutionResult:
        """Resolve source span against a single page's authoritative text."""
        clean_span = source_span.strip()
        if not clean_span:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="EMPTY_SOURCE_SPAN",
            )

        if not page_text or not page_text.strip():
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="PAGE_TEXT_EMPTY",
            )

        # 1. Exact substring match
        exact_idx = page_text.find(clean_span)
        if exact_idx != -1:
            end_idx = exact_idx + len(clean_span)
            return ResolutionResult(
                status=EvidenceValidationStatus.VALID,
                match_type=EvidenceMatchType.EXACT,
                char_start=exact_idx,
                char_end=end_idx,
                source_text=page_text[exact_idx:end_idx],
                reason=None,
            )

        # 2. Safe normalized-whitespace match
        norm_page, page_tokens = cls._normalize_whitespace_keep_tokens(page_text)
        norm_span, span_tokens = cls._normalize_whitespace_keep_tokens(clean_span)

        if not norm_span or not span_tokens:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="EMPTY_NORMALIZED_SPAN",
            )

        span_token_count = len(span_tokens)
        page_token_count = len(page_tokens)

        if span_token_count <= page_token_count:
            span_token_strings = norm_span.split()
            page_token_strings = norm_page.split()

            for i in range(page_token_count - span_token_count + 1):
                if page_token_strings[i : i + span_token_count] == span_token_strings:
                    orig_start = page_tokens[i][0]
                    orig_end = page_tokens[i + span_token_count - 1][1]
                    matched_text = page_text[orig_start:orig_end]
                    return ResolutionResult(
                        status=EvidenceValidationStatus.VALID,
                        match_type=EvidenceMatchType.NORMALIZED_WHITESPACE,
                        char_start=orig_start,
                        char_end=orig_end,
                        source_text=matched_text,
                        reason=None,
                    )

        return ResolutionResult(
            status=EvidenceValidationStatus.INVALID,
            match_type=EvidenceMatchType.UNMATCHED,
            char_start=None,
            char_end=None,
            source_text=None,
            reason="SPAN_NOT_FOUND_ON_PAGE",
        )

    @classmethod
    def resolve_cross_page(
        cls,
        page_texts: dict[int, str],
        page_start: int,
        page_end: int,
        source_span: str,
    ) -> ResolutionResult:
        """Resolve source span spanning across contiguous pages."""
        clean_span = source_span.strip()
        if not clean_span:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="EMPTY_SOURCE_SPAN",
            )

        if page_end < page_start:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="INVALID_PAGE_RANGE",
            )

        if page_end - page_start > cls.MAX_PAGE_RANGE:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="EXCESSIVE_PAGE_RANGE",
            )

        # Verify all intermediate pages exist
        for p in range(page_start, page_end + 1):
            if p not in page_texts:
                return ResolutionResult(
                    status=EvidenceValidationStatus.INVALID,
                    match_type=EvidenceMatchType.UNMATCHED,
                    char_start=None,
                    char_end=None,
                    source_text=None,
                    reason=f"PAGE_{p}_NOT_FOUND",
                )

        combined_text_parts: list[str] = []
        page_char_offsets: list[tuple[int, int, int]] = []
        current_offset = 0

        for p in range(page_start, page_end + 1):
            p_text = page_texts[p]
            start_off = current_offset
            end_off = start_off + len(p_text)
            page_char_offsets.append((p, start_off, end_off))
            combined_text_parts.append(p_text)
            current_offset = end_off + 1

        combined_text = "\n".join(combined_text_parts)

        # 1. Exact match in combined text
        exact_idx = combined_text.find(clean_span)
        if exact_idx != -1:
            end_idx = exact_idx + len(clean_span)
            start_page = next(p for p, s, e in page_char_offsets if exact_idx < e)
            end_page = next(p for p, s, e in page_char_offsets if (end_idx - 1) < e)

            if start_page == page_start and end_page == page_end:
                return ResolutionResult(
                    status=EvidenceValidationStatus.VALID,
                    match_type=EvidenceMatchType.CROSS_PAGE,
                    char_start=exact_idx,
                    char_end=end_idx,
                    source_text=combined_text[exact_idx:end_idx],
                    reason=None,
                )
            else:
                return ResolutionResult(
                    status=EvidenceValidationStatus.INVALID,
                    match_type=EvidenceMatchType.UNMATCHED,
                    char_start=None,
                    char_end=None,
                    source_text=None,
                    reason=(
                        f"PAGE_RANGE_MISMATCH_MATCHED_PAGES_{start_page}_TO_{end_page}"
                    ),
                )

        # 2. Normalized whitespace match across combined pages
        norm_comb, comb_tokens = cls._normalize_whitespace_keep_tokens(combined_text)
        norm_span, span_tokens = cls._normalize_whitespace_keep_tokens(clean_span)

        if not norm_span or not span_tokens:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="EMPTY_NORMALIZED_SPAN",
            )

        span_token_count = len(span_tokens)
        comb_token_count = len(comb_tokens)

        if span_token_count <= comb_token_count:
            span_token_strings = norm_span.split()
            comb_token_strings = norm_comb.split()

            for i in range(comb_token_count - span_token_count + 1):
                if comb_token_strings[i : i + span_token_count] == span_token_strings:
                    orig_start = comb_tokens[i][0]
                    orig_end = comb_tokens[i + span_token_count - 1][1]

                    start_page = next(
                        p for p, s, e in page_char_offsets if orig_start < e
                    )
                    end_page = next(
                        p for p, s, e in page_char_offsets if (orig_end - 1) < e
                    )

                    if start_page == page_start and end_page == page_end:
                        return ResolutionResult(
                            status=EvidenceValidationStatus.VALID,
                            match_type=EvidenceMatchType.CROSS_PAGE,
                            char_start=orig_start,
                            char_end=orig_end,
                            source_text=combined_text[orig_start:orig_end],
                            reason=None,
                        )
                    else:
                        return ResolutionResult(
                            status=EvidenceValidationStatus.INVALID,
                            match_type=EvidenceMatchType.UNMATCHED,
                            char_start=None,
                            char_end=None,
                            source_text=None,
                            reason=(
                                f"PAGE_RANGE_MISMATCH_MATCHED_PAGES_"
                                f"{start_page}_TO_{end_page}"
                            ),
                        )

        return ResolutionResult(
            status=EvidenceValidationStatus.INVALID,
            match_type=EvidenceMatchType.UNMATCHED,
            char_start=None,
            char_end=None,
            source_text=None,
            reason="CROSS_PAGE_SPAN_NOT_FOUND",
        )

    @classmethod
    def resolve(
        cls,
        page_texts: dict[int, str],
        page_start: int,
        page_end: int,
        source_span: str,
    ) -> ResolutionResult:
        """General resolver dispatching to single-page or cross-page resolution."""
        if page_start < 1 or page_end < 1:
            return ResolutionResult(
                status=EvidenceValidationStatus.INVALID,
                match_type=EvidenceMatchType.UNMATCHED,
                char_start=None,
                char_end=None,
                source_text=None,
                reason="INVALID_PAGE_NUMBER",
            )

        if page_start == page_end:
            if page_start not in page_texts:
                return ResolutionResult(
                    status=EvidenceValidationStatus.INVALID,
                    match_type=EvidenceMatchType.UNMATCHED,
                    char_start=None,
                    char_end=None,
                    source_text=None,
                    reason=f"PAGE_{page_start}_NOT_FOUND",
                )
            return cls.resolve_single_page(page_texts[page_start], source_span)
        else:
            return cls.resolve_cross_page(page_texts, page_start, page_end, source_span)
