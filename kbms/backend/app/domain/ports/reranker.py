from abc import ABC, abstractmethod


class Reranker(ABC):

    @abstractmethod
    def rerank_documents(self, query: str, documents: list[str]) -> list[float]: ...