import json
import logging

import dashscope

from app.domain.ports.reranker import Reranker
from app.infra.config.settings import Settings

logger = logging.getLogger(__name__)

class DashScopeReranker(Reranker):
    def __init__(self, settings: Settings):
        self._settings = settings

    def rerank_documents(self, query: str, documents: list[str]) -> list[float]:
        dashscope.api_key = self._settings.text_rerank_api_key
        response = dashscope.TextReRank.call(
            model = self._settings.text_rerank_model,
            query = query,
            documents = documents,
            top_n = len(documents),
            return_documents = False,
            instruct=self._settings.text_rerank_instruct,
        )
        logger.info(f"DashScope rerank response: \n{json.dumps(response, ensure_ascii=False, indent=2)}")

        status_code = response.get("status_code")
        if status_code != 200:
            message = response.get("message")
            raise RuntimeError(f"DashScope rerank failed: {message}")

        results = response.output.get("results",[])
        scores = [0.0] * len(documents)
        for item in results:
            index = item.get("index") # actual index of the document in the input!!!
            score = item.get("relevance_score")
            scores[int(index)] = float(score)
        return scores