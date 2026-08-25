from abc import ABC, abstractmethod


class Embedder(ABC):
   
    @abstractmethod
    def generate_embeddings(self, texts: list[str]) -> dict[str, list]: ...