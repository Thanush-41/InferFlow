from openai import AsyncOpenAI
from typing import AsyncGenerator, List, Dict, Optional
from app.sdk.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk
from app.config import get_settings


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._default_model = settings.default_openai_model

    async def generate(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> LLMResponse:
        model = model or self._default_model
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            model=model,
            finish_reason=choice.finish_reason or "",
        )

    async def generate_stream(self, messages: List[Dict[str, str]], model: str = None, **kwargs) -> AsyncGenerator[LLMStreamChunk, None]:
        model = model or self._default_model
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield LLMStreamChunk(
                    content=chunk.choices[0].delta.content,
                    is_final=False,
                )
            elif chunk.usage:
                yield LLMStreamChunk(
                    content="",
                    is_final=True,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )
