import json
from typing import Any

from app.domain.ports.reranker import Reranker
from app.workflows.query.base import NodeBase
from app.workflows.query.state import QueryGraphState

# -----------------------------
# Rerank / TopK Global Constants
# -----------------------------
# upper bound for dynamic TopK: maximum number of documents retained (<=10)
_RERANK_MAX_TOPK: int = 10
# minimum TopK guarantee: at least N documents are kept (>=1 and <= RERANK_MAX_TOPK)
_RERANK_MIN_TOPK: int = 3

# cliff detection thresholds (absolute): gap between high-scoring documents
_RERANK_GAP_ABS: float = 0.5
# cliff detection thresholds (relative): gap ratio for low-scoring tail documents
_RERANK_GAP_RATIO: float = 0.25

class NodeRerank(NodeBase):
    """
    Node: Re-rank RRF-fused results using a Cross-Encoder model.

    This node performs fine-grained relevance scoring on documents merged from
    multiple retrieval sources (local vector search + web search), then applies
    cliff detection to dynamically truncate the result list.
    """
    name: str = "node_rerank"

    def __init__(self, reranker: Reranker):
        super().__init__()
        self._reranker = reranker

    def _validate_input_state(self, state: QueryGraphState) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
        return (
            state.get('rewritten_query'),
            state.get('rrf_chunks'), 
            state.get('web_search_docs'),
        )

    def _merge_multi_source_docs(self, rrf_chunks, web_search_docs) -> list[dict[str, Any]]:
        """
        Merge documents from local retrieval and web search into a unified list.

        Local chunks are annotated with source="local" and url=None.
        Web documents are annotated with source="web" and chunk_id=None.

        Args:
            rrf_chunks: Chunks retrieved via local vector search and RRF fusion.
            web_search_docs: Documents retrieved via web search.

        Returns:
            A flattened list of documents ready for re-ranking.
        """
        merged_docs = []
        for rrf_doc in rrf_chunks:
            format_rrf_doc = {
                "content": rrf_doc.get('content'),
                "title": rrf_doc.get('item_name'),
                "chunk_id": rrf_doc.get('chunk_id'),
                "url": None,
                "source": "local"
            }
            merged_docs.append(format_rrf_doc)
        for web_doc in web_search_docs:
            format_web_doc = {
                "content": web_doc.get('snippet'),
                "title": web_doc.get('title'),
                "chunk_id": None,
                "url": web_doc.get('url'),
                "source": "web"
            }
            merged_docs.append(format_web_doc)
        return merged_docs

    def _rerank_merged_docs(self, rewritten_query: str, merged_multi_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Score and sort merged documents using a Cross-Encoder reranker.

        Unlike bi-encoders, Cross-Encoders jointly encode the query and each
        document, producing higher-precision relevance scores at the cost of
        increased compute.

        Args:
            rewritten_query: The (potentially rewritten) user query.
            merged_multi_docs: Unified document list from all retrieval sources.

        Returns:
            Documents sorted in descending order by relevance score.
            Each document is augmented with a "score" field.

        Note:
            On failure, logs the error and returns the input documents with
            score=None to allow graceful degradation.
        """
        try:
            contents = [doc.get("content") for doc in merged_multi_docs]
            rerank_scores = self._reranker.rerank_documents(rewritten_query, contents)

            scored_docs = [
                {**doc, "score": score} 
                for doc, score in zip(merged_multi_docs, rerank_scores)]
            
            return sorted(
                scored_docs,
                key=lambda doc: doc["score"],
                reverse=True
            )
        except Exception as e:
            self.logger.exception(f"Error reranking docs: {e!s}", stack_info=True)
            # Graceful fallback: return unsorted docs with no score
            return [{**doc, "score": None} for doc in merged_multi_docs]
        
    def _cliff_cutoff(self, ranked_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Dynamically truncate the ranked list using cliff detection.

        If the relevance score drops sharply between two adjacent documents
        (exceeding either absolute or relative gap thresholds), the list is
        truncated at that position. This prevents low-quality tail documents
        from polluting the final context fed to the LLM.

        Args:
            ranked_docs: Documents sorted in descending order by relevance score.

        Returns:
            A truncated list respecting MIN_TOPK and MAX_TOPK bounds.

        Algorithm:
            1. Upper bound = min(MAX_TOPK, len(ranked_docs))
            2. Lower bound = min(MIN_TOPK, upper_bound)
            3. Scan from lower_bound onward; truncate at the first detected cliff
            4. Default to upper_bound if no cliff is found
        """
        if not ranked_docs:
            return []
        upper_bound = min(_RERANK_MAX_TOPK, len(ranked_docs))
        lower_bound = min(_RERANK_MIN_TOPK, upper_bound)

        # retain up to the hard upper bound
        cutoff_pos = upper_bound

        # Scan from (lower_bound - 1) to (upper_bound - 2), inclusive
        # i.e., examine gaps between documents starting from MIN_TOPK
        # e.g. min_topk=3, max_topk=10 -> scan from 2,3,4,5,6,7,8, corresponding to docs 3-9
        for idx in range(lower_bound - 1, upper_bound - 1):
            current_score = ranked_docs[idx].get("score")
            next_score = ranked_docs[idx + 1].get("score")

            if current_score is None or next_score is None:
                continue
            abs_gap = current_score - next_score
            # Epsilon (1e-6) prevents division-by-zero on near-zero scores
            rel_gap = abs_gap / (abs(current_score) + 1e-6)

            # Truncate if either absolute or relative gap exceeds its threshold
            self.logger.info(f"Cliff detection, curr_idx={idx}, abs_gap={abs_gap:.4f}, rel_gap={rel_gap:.4f}")
            if abs_gap >= _RERANK_GAP_ABS or rel_gap >= _RERANK_GAP_RATIO:
                cutoff_pos = idx + 1
                self.logger.info(f"Cliff detected: {idx + 1}, abs_gap={abs_gap:.4f}, rel_gap={rel_gap:.4f}")
                break
        return ranked_docs[:cutoff_pos]

    def process(self, state: QueryGraphState) -> QueryGraphState:
        """
        Execute the full re-ranking pipeline.

        Pipeline steps:
            1. Merge documents from local RRF results and web search
            2. Compute fine-grained relevance scores via Cross-Encoder
            3. Apply cliff detection to dynamically truncate the result list
            4. Update the graph state with the final re-ranked documents

        Args:
            state: Graph state containing:
                - rewritten_query: The processed user query
                - rrf_chunks: Locally retrieved and RRF-fused chunks
                - web_search_docs: Web-retrieved documents

        Returns:
            Updated graph state with the "reranked_docs" key populated.

        Side Effects:
            Logs intermediate results and cliff detection decisions.
        """
        rewritten_query, rrf_chunks, web_search_docs = self._validate_input_state(state)

        # Step 1: Merge multi-source documents
        merged_multi_docs = self._merge_multi_source_docs(rrf_chunks, web_search_docs)
        self.logger.info(f"Merged {len(merged_multi_docs)} documents: \n{json.dumps(merged_multi_docs, indent=2, ensure_ascii=False)}")

        # Step 2: Cross-Encoder re-ranking
        reranked_docs = self._rerank_merged_docs(rewritten_query, merged_multi_docs)
        self.logger.info(f"Re-ranked {len(reranked_docs)} documents: \n{json.dumps(reranked_docs, indent=2, ensure_ascii=False)}")

        # Step 3: Dynamic TopK truncation via cliff detection
        cutoff_docs = self._cliff_cutoff(reranked_docs)
        self.logger.info(f"Final reranked documents after cliff cutoff: \n{json.dumps(cutoff_docs, indent=2, ensure_ascii=False)}")

        return {
            "reranked_docs": cutoff_docs
        }