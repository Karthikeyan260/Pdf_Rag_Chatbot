import uuid

import tiktoken

from app.services.pdf_processing.structure import SectionTracker, detect_headings
from app.services.pdf_processing.types import ChunkDraft, Heading, ImageExtract, PageText, TableExtract

PARENT_MAX_CHARS = 3000
CHILD_TARGET_CHARS = 700

_encoding = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def _split_paragraphs(raw_text: str) -> list[str]:
    paragraphs = [p.strip() for p in raw_text.replace("\r\n", "\n").split("\n\n")]
    return [p for p in paragraphs if p]


def chunk_document(pages: list[PageText], tables: list[TableExtract], images: list[ImageExtract]) -> list[ChunkDraft]:
    headings = detect_headings(pages)
    headings_by_page: dict[int, list[Heading]] = {}
    for h in headings:
        headings_by_page.setdefault(h.page_number, []).append(h)
    for page_headings in headings_by_page.values():
        page_headings.sort(key=lambda h: h.bbox[1])

    tracker = SectionTracker()
    drafts: list[ChunkDraft] = []
    page_to_parent_id: dict[int, str] = {}

    parent_id = uuid.uuid4().hex
    parent_start_page = pages[0].page_number if pages else 1
    parent_section_title = tracker.current_title
    parent_section_path = tracker.current_path
    parent_child_texts: list[str] = []
    child_buffer: list[str] = []
    child_buffer_page = parent_start_page

    def flush_child() -> None:
        nonlocal child_buffer
        if not child_buffer:
            return
        text = "\n\n".join(child_buffer)
        drafts.append(
            ChunkDraft(
                temp_id=uuid.uuid4().hex,
                text=text,
                chunk_type="text",
                page_number=child_buffer_page,
                section_title=parent_section_title,
                section_path=parent_section_path,
                token_count=_count_tokens(text),
                is_parent=False,
                parent_temp_id=parent_id,
            )
        )
        child_buffer = []

    def flush_parent() -> None:
        nonlocal parent_child_texts
        flush_child()
        if not parent_child_texts:
            return
        full_text = "\n\n".join(parent_child_texts)
        drafts.append(
            ChunkDraft(
                temp_id=parent_id,
                text=full_text,
                chunk_type="text",
                page_number=parent_start_page,
                section_title=parent_section_title,
                section_path=parent_section_path,
                token_count=_count_tokens(full_text),
                is_parent=True,
                parent_temp_id=None,
            )
        )
        parent_child_texts = []

    def start_new_section(heading: Heading) -> None:
        nonlocal parent_id, parent_start_page, parent_section_title, parent_section_path, child_buffer_page
        flush_parent()
        tracker.advance_to(heading)
        parent_id = uuid.uuid4().hex
        parent_start_page = heading.page_number
        parent_section_title = tracker.current_title
        parent_section_path = tracker.current_path
        child_buffer_page = heading.page_number

    for page in pages:
        page_to_parent_id[page.page_number] = parent_id
        page_headings = headings_by_page.get(page.page_number, [])
        heading_texts_lower = {h.text.strip().lower(): h for h in page_headings}

        for paragraph in _split_paragraphs(page.raw_text):
            matched_heading = None
            body_remainder = None

            normalized = paragraph.strip().lower()
            if normalized in heading_texts_lower:
                matched_heading = heading_texts_lower[normalized]
            else:
                for heading_text_lower, heading in heading_texts_lower.items():
                    if normalized.startswith(heading_text_lower) and len(heading_text_lower) > 3:
                        matched_heading = heading
                        body_remainder = paragraph[len(heading.text) :].strip()
                        break

            if matched_heading:
                start_new_section(matched_heading)
                page_to_parent_id[page.page_number] = parent_id
                if body_remainder:
                    child_buffer.append(body_remainder)
                    parent_child_texts.append(body_remainder)
                continue

            child_buffer.append(paragraph)
            parent_child_texts.append(paragraph)
            current_len = sum(len(c) for c in child_buffer)
            if current_len >= CHILD_TARGET_CHARS:
                flush_child()
                child_buffer_page = page.page_number

            if sum(len(t) for t in parent_child_texts) >= PARENT_MAX_CHARS:
                flush_parent()
                parent_id = uuid.uuid4().hex
                parent_start_page = page.page_number
                parent_section_title = tracker.current_title
                parent_section_path = tracker.current_path
                child_buffer_page = page.page_number
                page_to_parent_id[page.page_number] = parent_id

        child_buffer_page = page.page_number

    flush_parent()

    sorted_pages = sorted(page_to_parent_id.keys())

    def nearest_parent_for_page(page_number: int) -> str | None:
        candidates = [p for p in sorted_pages if p <= page_number]
        if candidates:
            return page_to_parent_id[max(candidates)]
        return page_to_parent_id[sorted_pages[0]] if sorted_pages else None

    for table in tables:
        drafts.append(
            ChunkDraft(
                temp_id=uuid.uuid4().hex,
                text=table.markdown,
                chunk_type="table",
                page_number=table.page_number,
                section_title=None,
                section_path=None,
                bbox=table.bbox,
                token_count=_count_tokens(table.markdown),
                is_parent=False,
                parent_temp_id=nearest_parent_for_page(table.page_number),
            )
        )

    for image in images:
        placeholder = f"[Figure on page {image.page_number}] (stored at {image.storage_path})"
        drafts.append(
            ChunkDraft(
                temp_id=uuid.uuid4().hex,
                text=placeholder,
                chunk_type="figure",
                page_number=image.page_number,
                section_title=None,
                section_path=None,
                bbox=image.bbox,
                token_count=_count_tokens(placeholder),
                is_parent=False,
                parent_temp_id=nearest_parent_for_page(image.page_number),
            )
        )

    return drafts
