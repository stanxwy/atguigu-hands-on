import json
from typing import Any

from app.workflows.query.base import NodeBase
from app.workflows.query.state import QueryGraphState

_WEIGHT_SEARCH_EMBEDDING = 1.0
_WEIGHT_HYDE = 1.0
_CONSTANT_K = 60

class NodeRrf(NodeBase):

    name: str = "node_rrf"

    def _rrf_merge(self, rrf_inputs, k: int = _CONSTANT_K, max_results: int | None = None) -> list[tuple[dict[str, Any], float]]:
        dict_score = {}
        dict_doc = {}

        for rrf_input, weight in rrf_inputs:
            for rank, doc in enumerate(rrf_input, start=1):
                chunk_id = doc.get('chunk_id')
                # RRF formula: score += weight / (k + rank)
                dict_score[chunk_id] = dict_score.get(chunk_id, 0.0) + weight / (k + rank)
                dict_doc.setdefault(chunk_id, doc)
        self.logger.info(f"dict_score: \n{json.dumps(dict_score, indent=2, ensure_ascii=False)}")
        self.logger.info(f"dict_doc: \n{json.dumps(dict_doc, indent=2, ensure_ascii=False)}")

        unsorted_results = [(dict_doc[chunk_id], score) for chunk_id, score in dict_score.items()]
        self.logger.info(f"unsorted_results: \n{json.dumps(unsorted_results, indent=2, ensure_ascii=False)}")

        sorted_results = sorted(
            unsorted_results,
            # sort by 2nd element of tuple i.e. score
            key=lambda result_entry: result_entry[1],
            reverse=True
        )
        self.logger.info(f"sorted_results: \n{json.dumps(sorted_results, indent=2, ensure_ascii=False)}")
        
        return sorted_results[:max_results] if max_results else sorted_results

    def process(self, state: QueryGraphState) -> QueryGraphState:
        
        embedding_search_list = [
            doc.get('entity') for doc in (state.get('embedding_chunks') or []) if isinstance(doc, dict)
        ]
        hyde_embedding_search_list = [
            doc.get('entity') for doc in (state.get('hyde_embedding_chunks') or []) if isinstance(doc, dict)
        ]

        # set weight for each result set from multi-query retrieval
        rrf_inputs = [
            (embedding_search_list, _WEIGHT_SEARCH_EMBEDDING),
            (hyde_embedding_search_list, _WEIGHT_HYDE)
        ]
        self.logger.info(f"rrf_inputs: \n{json.dumps(rrf_inputs, indent=2, ensure_ascii=False)}")

        rrf_merge_results = self._rrf_merge(rrf_inputs)

        # discard score
        rrf_chunks = [doc for doc, _ in rrf_merge_results]
        self.logger.info(f"rrf_chunks: \n{json.dumps(rrf_chunks, indent=2, ensure_ascii=False)}")

        return {
            'rrf_chunks': rrf_chunks
        }