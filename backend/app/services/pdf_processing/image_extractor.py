import os

import fitz  # PyMuPDF

from app.services.pdf_processing.types import ImageExtract

# Skip tiny images (icons, bullet glyphs, decorative rules) — not useful as standalone figures.
MIN_IMAGE_DIMENSION = 80


def extract_images(pdf_path: str, output_dir: str) -> list[ImageExtract]:
    doc = fitz.open(pdf_path)
    images: list[ImageExtract] = []
    try:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            for image_info in page.get_images(full=True):
                xref = image_info[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue
                width, height = base_image.get("width", 0), base_image.get("height", 0)
                if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                    continue

                ext = base_image.get("ext", "png")
                filename = f"page_{page_index + 1}_xref_{xref}.{ext}"
                path = os.path.join(output_dir, filename)
                with open(path, "wb") as f:
                    f.write(base_image["image"])

                bbox = None
                rects = page.get_image_rects(xref)
                if rects:
                    bbox = list(rects[0])

                images.append(ImageExtract(page_number=page_index + 1, bbox=bbox, storage_path=path))
    finally:
        doc.close()
    return images
