from app.services.pdf_processing.chunker import chunk_document
from app.services.pdf_processing.types import ImageExtract, PageText, TableExtract, TextSpan


def _span(text: str, size: float) -> TextSpan:
    return TextSpan(text=text, bbox=[0, 0, 100, size], font_size=size, is_bold=False)


def _make_page() -> PageText:
    raw_text = (
        "Chapter 1\n\n"
        "First paragraph text here about topic A.\n\n"
        "Second paragraph text here about topic B."
    )
    spans = [
        _span("Chapter 1", 24.0),
        _span("First paragraph text here about topic A.", 11.0),
        _span("Second paragraph text here about topic B.", 11.0),
    ]
    return PageText(page_number=1, raw_text=raw_text, spans=spans)


def test_chunk_document_builds_parent_child_text_chunks():
    drafts = chunk_document([_make_page()], tables=[], images=[])

    parents = [d for d in drafts if d.is_parent]
    children = [d for d in drafts if not d.is_parent]

    assert len(parents) == 1
    assert len(children) == 1
    assert children[0].parent_temp_id == parents[0].temp_id
    assert parents[0].section_title == "Chapter 1"
    assert "First paragraph" in parents[0].text
    assert "Second paragraph" in parents[0].text


def test_chunk_document_links_tables_and_figures_to_enclosing_section():
    table = TableExtract(page_number=1, bbox=[0, 0, 10, 10], rows=[["A", "B"], ["1", "2"]], markdown="| A | B |\n| --- | --- |\n| 1 | 2 |")
    image = ImageExtract(page_number=1, bbox=[0, 0, 10, 10], storage_path="/tmp/fig.png")

    drafts = chunk_document([_make_page()], tables=[table], images=[image])

    parent = next(d for d in drafts if d.is_parent)
    table_draft = next(d for d in drafts if d.chunk_type == "table")
    figure_draft = next(d for d in drafts if d.chunk_type == "figure")

    assert table_draft.parent_temp_id == parent.temp_id
    assert "| A | B |" in table_draft.text
    assert figure_draft.parent_temp_id == parent.temp_id
    assert "page 1" in figure_draft.text
