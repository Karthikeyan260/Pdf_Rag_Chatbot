from app.services.retrieval.compression import compress_context


def _chunk(text: str, page: int = 1, section: str | None = "Intro") -> dict:
    return {"text": text, "page_number": page, "section_title": section}


def test_dedupes_near_identical_chunks():
    chunks = [_chunk("Revenue grew 12% year over year in fiscal 2024."), _chunk("Revenue grew 12% year over year in fiscal 2024.")]
    context, included = compress_context(chunks, token_budget=1000)
    assert len(included) == 1
    assert "[1]" in context


def test_respects_token_budget():
    short_chunk = _chunk("a short passage")
    long_chunk = _chunk("word " * 2000)
    # short_chunk ranks first and fits; the oversized long_chunk that follows is
    # dropped rather than blowing the remaining budget.
    context, included = compress_context([short_chunk, long_chunk], token_budget=50)
    assert any(c["text"] == short_chunk["text"] for c in included)
    assert all(c["text"] != long_chunk["text"] for c in included)


def test_always_includes_at_least_the_top_chunk_even_if_it_is_large():
    only_chunk = _chunk("word " * 10)
    context, included = compress_context([only_chunk], token_budget=1)
    assert len(included) == 1
