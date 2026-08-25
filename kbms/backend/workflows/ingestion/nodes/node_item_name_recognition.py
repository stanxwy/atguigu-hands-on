from app.domain.ports.embedder import Embedder
from app.domain.ports.llm import LLMPort
from app.domain.ports.vector_db import ItemNameVectorDB
from app.workflows.ingestion.base import BaseNode
from app.workflows.ingestion.exceptions import StateFieldError
from app.workflows.ingestion.state import ImportGraphState


class NodeItemNameRecognition(BaseNode):

    name: str = "node_item_name_recognition"

    def __init__(self, 
                 llm_service: LLMPort,
                 embedding_service: Embedder, 
                 item_name_vector_db: ItemNameVectorDB):
        super().__init__()
        self._llm_service = llm_service
        self._embedding_service = embedding_service
        self._item_name_vector_db = item_name_vector_db

    def _validate_input_state(self, state: ImportGraphState) -> tuple[str, list[dict]]:
        file_title = state.get("file_title")
        if not file_title:
            raise StateFieldError(field_name="file_title", message="File title cannot be empty", expected_type=str)

        chunks = state.get("chunks")
        if not chunks:
            raise StateFieldError(field_name="chunks", message="Chunks cannot be empty", expected_type=list)

        if not isinstance(chunks, list):
            raise StateFieldError(field_name="chunks", message="Invalid data type for chunks", expected_type=list)

        return file_title, chunks

    def _build_llm_context(self, chunks: list[dict]) -> str:
        max_context_size = self.config.item_name_chunk_size
        parts: list[str] = []
        total_chars = 0
        for idx, chunk in enumerate(chunks[:self.config.item_name_chunk_k], start = 1):
            chunk_title = chunk.get("title").strip()
            chunk_content = chunk.get("content").strip()
            part = f"【切片{idx}】\n标题{chunk_title}\n内容：{chunk_content}"
            parts.append(part)

            total_chars += len(part)
            if total_chars > max_context_size:
                self.logger.warning(f"Total chars {total_chars} exceeds size limit {max_context_size}, stop appending")
                break
        context = "\n\n".join(parts).strip()
        final_context = context[:max_context_size]
        self.logger.info(f"context size for identification: {len(final_context)}")
        return final_context

    def _save_to_vector_db(self, file_title: str, item_name: str, dense_vector, sparse_vector):
        try:
            self._item_name_vector_db.create_collection()
            # idempotent operation
            self._item_name_vector_db.delete_data_by_file_title(file_title)

            data = {
                "file_title": file_title,
                "item_name": item_name
            }
            if dense_vector is not None:
                data["dense_vector"] = dense_vector
            if sparse_vector is not None:
                data["sparse_vector"] = sparse_vector

            self._item_name_vector_db.insert_data([data])
        except Exception as e: # catch exceptions but do not interrupt the flow
            self.logger.warning(f"Error inserting data into vector db: {e!s}", exc_info=True)

    def process(self, state: ImportGraphState) -> ImportGraphState:

        filename, chunks = self._validate_input_state(state)

        context = self._build_llm_context(chunks)

        item_name = self._llm_service.identify_main_product(filename, context)

        chunks = [{"item_name": item_name, **chunk} for chunk in chunks]

        vectors = self._embedding_service.generate_embeddings([item_name])

        self._save_to_vector_db(filename, item_name, vectors["dense"][0], vectors["sparse"][0])

        self.backup_json(state, chunks, "chunks.json")

        return {
            "chunks": chunks,
            "item_name": item_name
        }


