import pytest

from app.services.pdf_processing.validator import PDFValidationError, validate_pdf_bytes


def test_valid_pdf_passes():
    validate_pdf_bytes(b"%PDF-1.4\n...rest of a pdf...", "report.pdf")


def test_rejects_non_pdf_extension():
    with pytest.raises(PDFValidationError):
        validate_pdf_bytes(b"%PDF-1.4\n", "report.docx")


def test_rejects_bad_magic_bytes():
    with pytest.raises(PDFValidationError):
        validate_pdf_bytes(b"not a pdf at all", "report.pdf")


def test_rejects_empty_file():
    with pytest.raises(PDFValidationError):
        validate_pdf_bytes(b"", "report.pdf")


def test_rejects_oversized_file(monkeypatch):
    from app.services.pdf_processing import validator

    monkeypatch.setattr(validator.settings, "max_upload_size_mb", 0)
    with pytest.raises(PDFValidationError):
        validate_pdf_bytes(b"%PDF-1.4\nsome bytes", "report.pdf")
