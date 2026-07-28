import statistics

from app.services.pdf_processing.types import Heading, PageText

MAX_HEADING_CHARS = 120
HEADING_SIZE_RATIO = 1.15  # a span must be at least this many times the body font size to count as a heading


def _body_font_size(pages: list[PageText]) -> float:
    sizes = [span.font_size for page in pages for span in page.spans if span.font_size > 0]
    return statistics.median(sizes) if sizes else 10.0


def detect_headings(pages: list[PageText]) -> list[Heading]:
    body_size = _body_font_size(pages)
    distinct_sizes = sorted(
        {round(span.font_size, 1) for page in pages for span in page.spans if span.font_size >= body_size * HEADING_SIZE_RATIO},
        reverse=True,
    )
    # Map the (few) larger-than-body font sizes to heading levels 1..3+, biggest first.
    level_by_size = {size: min(index + 1, 3) for index, size in enumerate(distinct_sizes)}

    headings: list[Heading] = []
    for page in pages:
        for span in page.spans:
            size = round(span.font_size, 1)
            text = span.text.strip()
            if size not in level_by_size:
                continue
            if not text or len(text) > MAX_HEADING_CHARS:
                continue
            headings.append(Heading(page_number=page.page_number, text=text, level=level_by_size[size], bbox=span.bbox))
    return headings


class SectionTracker:
    """Maintains a running heading stack to build a breadcrumb `section_path` per page."""

    def __init__(self) -> None:
        self._stack: list[tuple[int, str]] = []  # (level, text)

    def advance_to(self, heading: Heading) -> None:
        self._stack = [entry for entry in self._stack if entry[0] < heading.level]
        self._stack.append((heading.level, heading.text))

    @property
    def current_title(self) -> str | None:
        return self._stack[-1][1] if self._stack else None

    @property
    def current_path(self) -> str | None:
        return " > ".join(text for _, text in self._stack) if self._stack else None
