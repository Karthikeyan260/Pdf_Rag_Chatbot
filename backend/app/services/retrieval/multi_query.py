from app.services.llm.base import BaseLLMProvider, LLMMessage

_SYSTEM_PROMPT = (
    "Given a search query, generate {count} alternative phrasings that would help retrieve "
    "relevant passages from a document via semantic search — vary vocabulary and specificity. "
    "Output exactly {count} lines, one query per line, no numbering, no extra commentary."
)


async def generate_query_variants(llm: BaseLLMProvider, query: str, count: int) -> list[str]:
    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT.format(count=count)),
        LLMMessage(role="user", content=query),
    ]
    response = await llm.generate(messages, temperature=0.5)
    variants = [line.strip("- ").strip() for line in response.content.splitlines() if line.strip()]
    return variants[:count] or [query]
