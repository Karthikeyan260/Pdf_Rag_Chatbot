import fitz  # PyMuPDF

from app.services.pdf_processing.types import PageText, TextSpan

# A page with fewer than this many extractable characters is treated as scanned/image-only.
SCANNED_TEXT_THRESHOLD = 20


def extract_pages(pdf_path: str) -> list[PageText]:
    doc = fitz.open(pdf_path)
    pages: list[PageText] = []
    try:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            raw_text = page.get_text("text")
            spans: list[TextSpan] = []

            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        font_flags = span.get("flags", 0)
                        is_bold = bool(font_flags & 2**4)
                        spans.append(
                            TextSpan(
                                text=text,
                                bbox=list(span.get("bbox", [0, 0, 0, 0])),
                                font_size=float(span.get("size", 0.0)),
                                is_bold=is_bold,
                            )
                        )

            pages.append(
                PageText(
                    page_number=page_index + 1,
                    raw_text=raw_text,
                    spans=spans,
                    is_scanned=len(raw_text.strip()) < SCANNED_TEXT_THRESHOLD,
                )
            )
    finally:
        doc.close()
    return pages


def get_page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def get_pdf_metadata(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    try:
        return dict(doc.metadata or {})
    finally:
        doc.close()
