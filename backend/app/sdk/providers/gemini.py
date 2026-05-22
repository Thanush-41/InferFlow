from google import genai
from google.genai import types
from typing import AsyncGenerator, List, Dict, Optional
from app.sdk.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk
from app.config import get_settings

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self._default_model = settings.default_model

    def _build_contents(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert standard messages to Gemini contents format."""
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"])]))
            elif msg["role"] == "assistant":
                contents.append(types.Content(role="model", parts=[types.Part(text=msg["content"])]))

        return system_instruction, contents

    async def generate(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> LLMResponse:
        model = model or self._default_model
        system_instruction, contents = self._build_contents(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction or DEFAULT_SYSTEM_PROMPT
        )

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        usage = response.usage_metadata
        return LLMResponse(
            content=response.text or "",
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
            total_tokens=usage.total_token_count if usage else None,
            model=model,
        )

    async def generate_stream(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> AsyncGenerator[LLMStreamChunk, None]:
        model = model or self._default_model
        system_instruction, contents = self._build_contents(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction or DEFAULT_SYSTEM_PROMPT
        )

        stream = await self.client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )
        async for chunk in stream:
            if chunk.text:
                is_final = chunk.usage_metadata is not None and chunk.usage_metadata.total_token_count > 0
                yield LLMStreamChunk(
                    content=chunk.text,
                    is_final=is_final,
                    input_tokens=chunk.usage_metadata.prompt_token_count if is_final and chunk.usage_metadata else None,
                    output_tokens=chunk.usage_metadata.candidates_token_count if is_final and chunk.usage_metadata else None,
                    total_tokens=chunk.usage_metadata.total_token_count if is_final and chunk.usage_metadata else None,
                )
