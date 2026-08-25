from app.domain.ports.embedder import Embedder
from app.workflows.ingestion.base import BaseNode
from app.workflows.ingestion.exceptions import StateFieldError
from app.workflows.ingestion.state import ImportGraphState

BATCH_SIZE = 5

class NodeBGEEmbedding(BaseNode):

    name: str = "node_bge_embedding"

    def __init__(self, embedding_service: Embedder):
        super().__init__()
        self._embedding_service = embedding_service

    def _validate_input_state(self, state: ImportGraphState) -> list[dict]:
        chunks = state.get("chunks")
        if not chunks:
            raise StateFieldError(field_name="chunks", message="Chunks cannot be empty", expected_type=list)

        if not isinstance(chunks, list):
            raise StateFieldError(field_name="chunks", message="Invalid data type for chunks", expected_type=list)
        return chunks

    def _batch_generate_embeddings(self, chunks: list[dict[str, str]]) -> list[dict[str, str]]:
        chunks_with_embeddings = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_chunks = chunks[i:i + BATCH_SIZE]
            concat_chunks = []
            for chunk in batch_chunks:
                item_name = chunk["item_name"]
                content = chunk["content"]
                concat_chunks.append(f"{item_name}\n{content}" if item_name else content)

            docs_embeddings = self._embedding_service.generate_embeddings(concat_chunks)
            for j, chunk in enumerate(batch_chunks):
                copied_chunk = chunk.copy()
                copied_chunk["dense_vector"] = docs_embeddings["dense"][j]
                copied_chunk["sparse_vector"] = docs_embeddings["sparse"][j]
                chunks_with_embeddings.append(copied_chunk)
            self.logger.info(f"Embeddings generated for chunks {i + 1}-{min(i + len(batch_chunks), len(chunks))}")

        return chunks_with_embeddings

    def process(self, state: ImportGraphState) -> ImportGraphState:

        chunks = self._validate_input_state(state)

        chunks_with_embeddings = self._batch_generate_embeddings(chunks)

        self.backup_json(state, chunks_with_embeddings, "chunks_with_embeddings.json")
        return {
            "chunks": chunks_with_embeddings
        }