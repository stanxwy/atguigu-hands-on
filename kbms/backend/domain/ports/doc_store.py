from abc import ABC, abstractmethod
from typing import Any


class DocumentStore(ABC):

    @abstractmethod
    def clear_history(self, session_id: str) -> int: ...

    @abstractmethod
    def save_chat_message(
        self,
        session_id: str,
        role: str,
        text: str,
        rewritten_query: str = "",
        item_names: list[str] | None = None,
        image_urls: list[str] | None = None,
        message_id: str | None = None
    ) -> str: ...

    @abstractmethod
    def update_message_item_names(self, ids: list[str], item_names: list[str]) -> int: ...

    @abstractmethod
    def get_recent_messages(self, session_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]: ...