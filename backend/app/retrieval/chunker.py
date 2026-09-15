import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.processing.models import DocumentPage
from app.retrieval.models import IndexingError, RetrievalChunk

# Regex for sentence splitting on standard legal terminators
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.?!;])\s+")


@dataclass(frozen=True)
class ChunkingConfig:
    """Configuration parameters for deterministic document chunking."""

    target_chunk_size: int = 600
    chunk_overlap: int = 120
    min_chunk_size: int = 80
    max_chunks_per_document: int = 2000


@dataclass
class _TextUnit:
    """Internal representation of an atomic text segment with page provenance."""

    text: str
    page_number: int
    page_id: str


class DocumentChunker:
    """Deterministic, page-aware text chunker with bounded overlap."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk_document(
        self,
        document_id: str,
        pages: Sequence[DocumentPage],
    ) -> list[RetrievalChunk]:
        """Split ordered DocumentPage objects into indexed RetrievalChunks.

        Maintains exact provenance (page_start, page_end, source_page_ids)
        and preserves exact source text without alterations.
        """
        if not pages:
            return []

        # 1. Collect ordered atomic text units from pages
        atomic_units: list[_TextUnit] = []
        for page in pages:
            if not page.text or page.is_empty:
                continue

            page_units = self._split_page_into_units(page)
            atomic_units.extend(page_units)

        if not atomic_units:
            return []

        # 2. Assemble units into bounded chunks with overlap
        chunks: list[RetrievalChunk] = []
        current_units: list[_TextUnit] = []
        current_len = 0
        chunk_index = 0

        i = 0
        while i < len(atomic_units):
            unit = atomic_units[i]
            current_units.append(unit)
            current_len += len(unit.text) + (1 if current_len > 0 else 0)

            # Check if target chunk size is reached
            if current_len >= self.config.target_chunk_size:
                chunk = self._build_chunk(document_id, chunk_index, current_units)
                chunks.append(chunk)
                chunk_index += 1

                if len(chunks) > self.config.max_chunks_per_document:
                    raise IndexingError(
                        f"Document '{document_id}' exceeded maximum chunk limit "
                        f"of {self.config.max_chunks_per_document}."
                    )

                # Compute overlap for next chunk
                overlap_units = self._compute_overlap_units(current_units)
                current_units = list(overlap_units)
                current_len = sum(len(u.text) for u in current_units) + max(
                    0, len(current_units) - 1
                )

            i += 1

        # Handle remaining trailing units
        if current_units:
            trailing_text = " ".join(u.text for u in current_units).strip()
            # If trailing text is meaningful, add it as the final chunk
            if len(trailing_text) >= self.config.min_chunk_size or not chunks:
                chunk = self._build_chunk(document_id, chunk_index, current_units)
                chunks.append(chunk)
            elif chunks:
                # Merge small trailing fragment into previous chunk if small
                last_chunk = chunks[-1]
                updated_page_end = max(
                    last_chunk.page_end, current_units[-1].page_number
                )
                updated_page_ids = list(
                    dict.fromkeys(
                        last_chunk.source_page_ids
                        + [u.page_id for u in current_units if u.page_id]
                    )
                )
                merged_text = f"{last_chunk.text} {trailing_text}".strip()

                chunks[-1] = RetrievalChunk.create(
                    chunk_id=last_chunk.id,
                    document_id=document_id,
                    chunk_index=last_chunk.chunk_index,
                    text=merged_text,
                    page_start=last_chunk.page_start,
                    page_end=updated_page_end,
                    source_page_ids=updated_page_ids,
                )

        return chunks

    def _split_page_into_units(self, page: DocumentPage) -> list[_TextUnit]:
        """Split a page into atomic paragraph/sentence units."""
        units: list[_TextUnit] = []
        raw_paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]

        for p in raw_paragraphs:
            if len(p) <= self.config.target_chunk_size:
                units.append(
                    _TextUnit(text=p, page_number=page.page_number, page_id=page.id)
                )
            else:
                # Paragraph exceeds target size: split by sentences
                sentences = [
                    s.strip() for s in SENTENCE_SPLIT_REGEX.split(p) if s.strip()
                ]
                for s in sentences:
                    units.append(
                        _TextUnit(
                            text=s,
                            page_number=page.page_number,
                            page_id=page.id,
                        )
                    )

        return units

    def _compute_overlap_units(self, units: list[_TextUnit]) -> list[_TextUnit]:
        """Compute the trailing units to carry over into the next chunk for overlap."""
        overlap: list[_TextUnit] = []
        accumulated_len = 0

        for unit in reversed(units):
            if accumulated_len + len(unit.text) > self.config.chunk_overlap and overlap:
                break
            overlap.insert(0, unit)
            accumulated_len += len(unit.text)

        # Ensure we never duplicate 100% of the previous chunk
        if len(overlap) == len(units) and len(units) > 1:
            overlap = overlap[1:]

        return overlap

    def _build_chunk(
        self,
        document_id: str,
        chunk_index: int,
        units: list[_TextUnit],
    ) -> RetrievalChunk:
        """Construct a validated RetrievalChunk from a sequence of text units."""
        chunk_text = " ".join(u.text for u in units).strip()
        page_start = min(u.page_number for u in units)
        page_end = max(u.page_number for u in units)
        source_page_ids = list(dict.fromkeys(u.page_id for u in units if u.page_id))

        return RetrievalChunk.create(
            document_id=document_id,
            chunk_index=chunk_index,
            text=chunk_text,
            page_start=page_start,
            page_end=page_end,
            source_page_ids=source_page_ids,
        )
