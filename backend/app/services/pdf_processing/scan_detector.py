from app.services.pdf_processing.types import PageText


def find_scanned_pages(pages: list[PageText]) -> list[int]:
    """Return page numbers that look image-only (no usable extracted text layer)."""
    return [p.page_number for p in pages if p.is_scanned]
