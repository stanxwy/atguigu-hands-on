
from abc import ABC, abstractmethod


class VectorDB(ABC):

    @abstractmethod
    def create_collection(self, dense_vector_dim: int | None = None): ...

    @abstractmethod
    def insert_data(self, data: list[dict]) -> int: ...

    @abstractmethod
    def delete_data_by_file_title(self, file_title: str) -> int: ...


class ItemNameVectorDB(VectorDB):
    
    @abstractmethod
    def hybrid_search_item_name(self, item_names: list[str]) -> list[dict]: ...


class ChunksVectorDB(VectorDB):

    @abstractmethod
    def hybrid_search_chunks(self, input_text: str, item_names: list[str]) -> list[dict]: ...