import logging

from FlagEmbedding import FlagReranker

from app.domain.ports.reranker import Reranker
from app.infra.config.settings import Settings

logger = logging.getLogger(__name__)

class BGEReranker(Reranker):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None

    def _get_reranker_model(self) -> FlagReranker:
        if self._model is None:
            try:
                config = self._settings
                logger.info(f"Initializing Reranker...\n{config}")
                self._model = FlagReranker(
                    model_name_or_path=config.bge_rerank_model,
                    devices=config.bge_rerank_device,
                    use_fp16=config.bge_rerank_fp16,
                    normalize=True,
                    query_instruction_for_rerank=config.text_rerank_instruct,
                )
                logger.info("Reranker initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reranker : {e}", exc_info=True)
        return self._model

    def rerank_documents(self, query: str, documents: list[str]) -> list[float]:
        pairs = [(query, doc) for doc in documents]
        return self._get_reranker_model().compute_score(pairs)