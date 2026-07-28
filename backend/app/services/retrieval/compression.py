import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def compress_context(ranked_chunks: list[dict], token_budget: int) -> tuple[str, list[dict]]:
    """Deduplicate near-identical chunks and trim to a token budget, best-ranked first.

    Returns the assembled context string (chunks numbered [1], [2], ... for citation
    markers the LLM is asked to use) and the list of chunks actually included.
    """
    seen_prefixes: set[str] = set()
    included: list[dict] = []
    used_tokens = 0

    for chunk in ranked_chunks:
        prefix = chunk["text"][:120].strip().lower()
        if prefix in seen_prefixes:
            continue

        tokens = _count_tokens(chunk["text"])
        if included and used_tokens + tokens > token_budget:
            continue
        # A lone oversized top result is still included (better to slightly exceed
        # the budget than send the LLM no context at all); only reject it for being
        # too large once something else has already been included.
        if included and tokens > token_budget:
            continue

        seen_prefixes.add(prefix)
        included.append(chunk)
        used_tokens += tokens

    context_parts = []
    for i, chunk in enumerate(included, start=1):
        section = f" (Section: {chunk['section_title']})" if chunk.get("section_title") else ""
        context_parts.append(f"[{i}] Page {chunk['page_number']}{section}:\n{chunk['text']}")

    return "\n\n".join(context_parts), included
