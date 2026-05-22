from typing import AsyncGenerator, List, Dict, Optional
from app.sdk.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk
from app.sdk.providers.gemini import GeminiProvider
from app.sdk.providers.openai_provider import OpenAIProvider
from app.sdk.logger import inference_logger
from app.config import get_settings


class LLMWrapper:
    """
    Lightweight SDK wrapper around LLM calls.
    Automatically captures inference metadata and logs to ingestion pipeline.
    """

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize available providers."""
        try:
            self.providers["gemini"] = GeminiProvider()
        except Exception as e:
            print(f"[LLMWrapper] Gemini provider init failed: {e}")

        try:
            self.providers["openai"] = OpenAIProvider()
        except Exception as e:
            print(f"[LLMWrapper] OpenAI provider init failed: {e}")

    def get_provider(self, provider_name: str) -> BaseLLMProvider:
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available. Available: {list(self.providers.keys())}")
        return self.providers[provider_name]

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: str,
        conversation_id: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a response with full inference logging."""
        llm_provider = self.get_provider(provider)
        context = inference_logger.start_request(conversation_id, model, provider)

        input_preview = messages[-1]["content"] if messages else ""

        try:
            response = await llm_provider.generate(messages, model, **kwargs)

            await inference_logger.end_request(
                context=context,
                status="success",
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
                input_preview=input_preview,
                output_preview=response.content[:get_settings().preview_max_length],
                is_streaming=False,
            )
            return response

        except Exception as e:
            await inference_logger.end_request(
                context=context,
                status="error",
                error_message=str(e),
                input_preview=input_preview,
                is_streaming=False,
            )
            raise

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: str,
        conversation_id: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response with inference logging."""
        llm_provider = self.get_provider(provider)
        context = inference_logger.start_request(conversation_id, model, provider)

        input_preview = messages[-1]["content"] if messages else ""
        full_content = []
        final_tokens = {}

        try:
            async for chunk in llm_provider.generate_stream(messages, model, **kwargs):
                if chunk.content:
                    if not full_content:
                        inference_logger.mark_first_token(context)
                    full_content.append(chunk.content)
                    yield chunk.content

                if chunk.is_final:
                    final_tokens = {
                        "input_tokens": chunk.input_tokens,
                        "output_tokens": chunk.output_tokens,
                        "total_tokens": chunk.total_tokens,
                    }

            output = "".join(full_content)
            await inference_logger.end_request(
                context=context,
                status="success",
                input_preview=input_preview,
                output_preview=output[:get_settings().preview_max_length],
                is_streaming=True,
                **final_tokens,
            )

        except Exception as e:
            await inference_logger.end_request(
                context=context,
                status="error",
                error_message=str(e),
                input_preview=input_preview,
                is_streaming=True,
            )
            raise


# Singleton
llm_wrapper = LLMWrapper()
