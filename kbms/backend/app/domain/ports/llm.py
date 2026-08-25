from abc import ABC, abstractmethod
from typing import Any

from langchain_openai import ChatOpenAI


class LLMPort(ABC):

    @abstractmethod
    def get_llm_client(self, model: str | None = None, json_mode: bool = False) -> ChatOpenAI: ...

    @abstractmethod
    def generate_image_caption(self, image_path: str, doc_stem: str, image_context: tuple[str, str]) -> str: ...

    @abstractmethod
    def identify_main_product(self, filename: str, context: str) -> str: ...

    @abstractmethod
    def resolve_item_name_and_rewrite_query(self, query: str, history: list[dict[str, Any]]) -> tuple[list[str], str]: ...

    @abstractmethod
    def generate_hyde_doc(self, rewritten_query: str) -> str: ...