import pdfplumber

from app.services.pdf_processing.types import TableExtract


def _rows_to_markdown(rows: list[list[str | None]]) -> str:
    if not rows:
        return ""
    cleaned = [[(cell or "").strip().replace("\n", " ") for cell in row] for row in rows]
    header, *body = cleaned
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def extract_tables(pdf_path: str) -> list[TableExtract]:
    tables: list[TableExtract] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            found_tables = page.find_tables()
            for table in found_tables:
                rows = table.extract()
                if not rows or all(not any(cell for cell in row) for row in rows):
                    continue
                tables.append(
                    TableExtract(
                        page_number=page_index + 1,
                        bbox=list(table.bbox) if table.bbox else None,
                        rows=rows,
                        markdown=_rows_to_markdown(rows),
                    )
                )
    return tables
