from abc import ABC, abstractmethod
from threading import Lock

from app.processing.models import DocumentPage


class PageRepository(ABC):
    """Abstract interface for storing and retrieving document page records."""

    @abstractmethod
    def save_pages(
        self, document_id: str, pages: list[DocumentPage]
    ) -> list[DocumentPage]:
        """Save pages for a document, replacing previous records idempotently."""
        pass

    @abstractmethod
    def get_pages_by_document(self, document_id: str) -> list[DocumentPage]:
        """Retrieve all pages for a document ordered by page_number ascending."""
        pass

    @abstractmethod
    def get_page(self, document_id: str, page_number: int) -> DocumentPage | None:
        """Retrieve a specific page by document ID and page number."""
        pass

    @abstractmethod
    def delete_pages_by_document(self, document_id: str) -> int:
        """Delete all page records for a document."""
        pass

    @abstractmethod
    def count_pages(self, document_id: str) -> int:
        """Return the number of pages stored for a document."""
        pass


class InMemoryPageRepository(PageRepository):
    """Thread-safe in-memory page repository implementation."""

    def __init__(self) -> None:
        self._lock = Lock()
        # Key: (document_id, page_number) -> DocumentPage
        self._pages: dict[tuple[str, int], DocumentPage] = {}

    def save_pages(
        self, document_id: str, pages: list[DocumentPage]
    ) -> list[DocumentPage]:
        with self._lock:
            # Atomic replacement: first delete any existing pages for document
            keys_to_remove = [k for k in self._pages if k[0] == document_id]
            for k in keys_to_remove:
                del self._pages[k]

            # Save new pages
            for page in pages:
                self._pages[(document_id, page.page_number)] = page

            # Return sorted pages
            return sorted(
                [p for p in self._pages.values() if p.document_id == document_id],
                key=lambda p: p.page_number,
            )

    def get_pages_by_document(self, document_id: str) -> list[DocumentPage]:
        with self._lock:
            return sorted(
                [p for p in self._pages.values() if p.document_id == document_id],
                key=lambda p: p.page_number,
            )

    def get_page(self, document_id: str, page_number: int) -> DocumentPage | None:
        with self._lock:
            return self._pages.get((document_id, page_number))

    def delete_pages_by_document(self, document_id: str) -> int:
        with self._lock:
            keys_to_remove = [k for k in self._pages if k[0] == document_id]
            count = len(keys_to_remove)
            for k in keys_to_remove:
                del self._pages[k]
            return count

    def count_pages(self, document_id: str) -> int:
        with self._lock:
            return sum(1 for k in self._pages if k[0] == document_id)


# Global singleton repository instance
in_memory_page_repository = InMemoryPageRepository()
