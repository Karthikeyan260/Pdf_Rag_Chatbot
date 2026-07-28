from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

settings = get_settings()

_ROLE_MAP = {"user": "user", "assistant": "model"}


class GeminiProvider(BaseLLMProvider):
    """Live adapter for Gemini 2.5 via the `google-genai` SDK (the successor to the
    now end-of-life `google-generativeai` package — that package stopped receiving
    updates/fixes, so this adapter targets its replacement instead).
    """

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_model

    def _build_request(self, messages: list[LLMMessage]) -> tuple[list[types.Content], types.GenerateContentConfig]:
        system_instruction = "\n".join(m.content for m in messages if m.role == "system") or None
        contents = [
            types.Content(role=_ROLE_MAP.get(m.role, "user"), parts=[types.Part(text=m.content)])
            for m in messages
            if m.role != "system"
        ]
        return contents, system_instruction

    async def generate(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        contents, system_instruction = self._build_request(messages)
        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=temperature),
        )
        usage = response.usage_metadata
        return LLMResponse(
            content=response.text or "",
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )

    async def stream(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> AsyncIterator[str]:
        contents, system_instruction = self._build_request(messages)
        stream = await self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=temperature),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
