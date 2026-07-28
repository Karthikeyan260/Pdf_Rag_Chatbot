from app.services.pdf_processing.structure import SectionTracker, detect_headings
from app.services.pdf_processing.types import PageText, TextSpan


def _span(text: str, size: float) -> TextSpan:
    return TextSpan(text=text, bbox=[0, 0, 100, size], font_size=size, is_bold=False)


def test_detect_headings_picks_out_larger_font_spans():
    pages = [
        PageText(
            page_number=1,
            raw_text="Introduction\nBody text at normal size explaining things.",
            spans=[_span("Introduction", 24.0), _span("Body text at normal size explaining things.", 11.0)],
        )
    ]
    headings = detect_headings(pages)
    assert len(headings) == 1
    assert headings[0].text == "Introduction"
    assert headings[0].level == 1


def test_detect_headings_ignores_uniform_font_size():
    pages = [
        PageText(
            page_number=1,
            raw_text="All body text, no headings here at all.",
            spans=[_span("All body text, no headings here at all.", 11.0), _span("More body text of the same size.", 11.0)],
        )
    ]
    assert detect_headings(pages) == []


def test_section_tracker_builds_breadcrumb_and_pops_deeper_levels():
    tracker = SectionTracker()
    headings = detect_headings(
        [
            PageText(
                page_number=1,
                raw_text="",
                spans=[
                    _span("Body paragraph one.", 11.0),
                    _span("Body paragraph two.", 11.0),
                    _span("Chapter 1", 24.0),
                    _span("Section 1.1", 18.0),
                ],
            ),
        ]
    )
    h1 = next(h for h in headings if h.text == "Chapter 1")
    h2 = next(h for h in headings if h.text == "Section 1.1")

    tracker.advance_to(h1)
    assert tracker.current_path == "Chapter 1"

    tracker.advance_to(h2)
    assert tracker.current_path == "Chapter 1 > Section 1.1"

    # Advancing to another top-level heading pops the deeper one.
    tracker.advance_to(h1)
    assert tracker.current_path == "Chapter 1"
