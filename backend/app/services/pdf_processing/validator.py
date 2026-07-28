from app.core.config import get_settings

settings = get_settings()

PDF_MAGIC = b"%PDF-"


class PDFValidationError(ValueError):
    pass


def validate_pdf_bytes(data: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise PDFValidationError("File must have a .pdf extension")

    if not data.startswith(PDF_MAGIC):
        raise PDFValidationError("File does not look like a valid PDF (bad magic bytes)")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise PDFValidationError(f"File exceeds max upload size of {settings.max_upload_size_mb}MB")

    if len(data) == 0:
        raise PDFValidationError("File is empty")
