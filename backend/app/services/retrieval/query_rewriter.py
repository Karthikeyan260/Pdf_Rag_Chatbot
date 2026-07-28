from app.services.llm.base import BaseLLMProvider, LLMMessage

_SYSTEM_PROMPT = (
    "You rewrite a user's latest chat message into a single, fully self-contained search "
    "query. Resolve pronouns and implicit references using the conversation history. "
    "Do not answer the question — only output the rewritten query, nothing else."
)


async def rewrite_query(llm: BaseLLMProvider, question: str, history: list[dict]) -> str:
    if not history:
        return question

    history_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-6:])
    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=f"Conversation history:\n{history_text}\n\nLatest message: {question}\n\nRewritten query:",
        ),
    ]
    response = await llm.generate(messages, temperature=0.0)
    rewritten = response.content.strip().strip('"')
    return rewritten or question
