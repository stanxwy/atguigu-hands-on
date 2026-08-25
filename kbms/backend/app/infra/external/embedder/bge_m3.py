from pymilvus.model.hybrid import BGEM3EmbeddingFunction

from app.domain.ports.embedder import Embedder
from app.infra.config.settings import Settings


class BgeM3Embedding(Embedder):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = BGEM3EmbeddingFunction(
                model_name=self._settings.bge_m3_path,
                device=self._settings.bge_device,
                use_fp16=self._settings.bge_fp16
            )
        return self._model

    def generate_embeddings(self, texts: list[str]) -> dict[str, list]:
        model = self._get_model()
        embeddings = model.encode_documents(texts)
        processed_sparse = []
        for i in range(len(texts)):
            start = embeddings["sparse"].indptr[i]
            end = embeddings["sparse"].indptr[i + 1]
            sparse_indices = embeddings["sparse"].indices[start:end].tolist()
            sparse_data = embeddings["sparse"].data[start:end].tolist()
            sparse_dict = {k: v for k, v in zip(sparse_indices, sparse_data)}
            processed_sparse.append(sparse_dict)
        return {
            "sparse": processed_sparse,
            "dense": [emb.tolist() for emb in embeddings["dense"]]
        }