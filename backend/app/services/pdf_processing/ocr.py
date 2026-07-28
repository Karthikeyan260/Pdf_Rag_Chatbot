import io

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from app.services.pdf_processing.types import PageText, TextSpan

OCR_RENDER_DPI = 200


def ocr_scanned_pages(pdf_path: str, pages: list[PageText]) -> list[PageText]:
    """Run OCR over pages flagged as scanned and replace their text in place.

    OCR output has no reliable font-size metadata, so OCR'd pages get a single
    synthetic span covering the whole page — they won't contribute to heading
    detection but are fully searchable and chunkable.
    """
    scanned_page_numbers = {p.page_number for p in pages if p.is_scanned}
    if not scanned_page_numbers:
        return pages

    doc = fitz.open(pdf_path)
    try:
        for page in pages:
            if page.page_number not in scanned_page_numbers:
                continue
            fitz_page = doc[page.page_number - 1]
            pixmap = fitz_page.get_pixmap(dpi=OCR_RENDER_DPI)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            ocr_text = pytesseract.image_to_string(image)
            page.raw_text = ocr_text
            if ocr_text.strip():
                page.spans = [
                    TextSpan(text=ocr_text.strip(), bbox=[0, 0, pixmap.width, pixmap.height], font_size=12.0, is_bold=False)
                ]
    finally:
        doc.close()
    return pages
