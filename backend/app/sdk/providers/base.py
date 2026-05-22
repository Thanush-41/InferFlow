from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model: str = ""
    finish_reason: str = ""


@dataclass
class LLMStreamChunk:
    content: str
    is_final: bool = False
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class BaseLLMProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(self, messages: List[Dict[str, str]], model: str, **kwargs) -> AsyncGenerator[LLMStreamChunk, None]:
        pass
