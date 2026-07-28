from app.services.llm.base import LLMMessage

ANSWER_SYSTEM_PROMPT = (
    "You are an enterprise document assistant. Answer ONLY using the numbered context "
    "passages below — never use outside knowledge. Cite every claim with the matching "
    "bracket marker, e.g. [1], [2]. If the passages don't contain the answer, say so "
    "plainly instead of guessing. Format the answer with Markdown (lists, tables, code "
    "blocks) where it improves readability."
)


def build_chat_messages(context: str, question: str, history: list[dict]) -> list[LLMMessage]:
    messages = [LLMMessage(role="system", content=ANSWER_SYSTEM_PROMPT)]
    for turn in history[-6:]:
        messages.append(LLMMessage(role=turn["role"], content=turn["content"]))
    messages.append(
        LLMMessage(
            role="user",
            content=f"Context passages:\n{context}\n\nQuestion: {question}",
        )
    )
    return messages


def build_citations(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "page_number": c["page_number"],
            "section_title": c.get("section_title"),
            "confidence_score": c["score"],
            "bbox": c.get("bbox"),
        }
        for c in chunks
    ]
