import logging

from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows.query.nodes.node_answer_output import NodeAnswerOutput
from app.workflows.query.nodes.node_item_name_confirm import (
    NodeItemNameConfirm,
)
from app.workflows.query.nodes.node_rerank import NodeRerank
from app.workflows.query.nodes.node_rrf import NodeRrf
from app.workflows.query.nodes.node_search_embedding import (
    NodeSearchEmbedding,
)
from app.workflows.query.nodes.node_search_embedding_hyde import (
    NodeSearchEmbeddingHyde,
)
from app.workflows.query.nodes.node_web_search_mcp import NodeWebSearchMcp
from app.workflows.query.state import QueryGraphState

logger = logging.getLogger(__name__)

class KBQueryWorkflow:
    
    def __init__(
        self, *, 
        node_item_name_confirm: NodeItemNameConfirm,
        node_search_embedding: NodeSearchEmbedding,
        node_search_embedding_hyde: NodeSearchEmbeddingHyde,
        node_web_search_mcp: NodeWebSearchMcp,
        node_rrf: NodeRrf,
        node_rerank: NodeRerank,
        node_answer_output: NodeAnswerOutput,
    ):
        self._graph = StateGraph(QueryGraphState)

        self.node_item_name_confirm = node_item_name_confirm
        self.node_search_embedding = node_search_embedding
        self.node_search_embedding_hyde = node_search_embedding_hyde
        self.node_web_search_mcp = node_web_search_mcp
        self.node_rrf = node_rrf
        self.node_rerank = node_rerank
        self.node_answer_output = node_answer_output

        self._register_nodes()
        self._setup_routes()
        self._compiled_graph: CompiledStateGraph | None = None

    def _register_nodes(self):
        self._graph.add_node("node_item_name_confirm", self.node_item_name_confirm)
        self._graph.add_node("node_search_embedding", self.node_search_embedding)
        self._graph.add_node("node_search_embedding_hyde", self.node_search_embedding_hyde) 
        self._graph.add_node("node_web_search_mcp", self.node_web_search_mcp)
        self._graph.add_node("node_rrf", self.node_rrf)
        self._graph.add_node("node_rerank", self.node_rerank)
        self._graph.add_node("node_answer_output", self.node_answer_output)

    def _route_after_item_name_confirm(self, state: QueryGraphState) -> str | list[str]:
        if state.get("answer"):
            return "node_answer_output"
        return ["node_search_embedding", "node_search_embedding_hyde", "node_web_search_mcp"]

    def _setup_routes(self):
        self._graph.set_entry_point("node_item_name_confirm")
        self._graph.add_conditional_edges(
            "node_item_name_confirm",
            self._route_after_item_name_confirm,
            {
                "node_answer_output": "node_answer_output",
                "node_search_embedding": "node_search_embedding",
                "node_search_embedding_hyde": "node_search_embedding_hyde",
                "node_web_search_mcp": "node_web_search_mcp"
            }
        )
        self._graph.add_edge("node_search_embedding", "node_rrf")
        self._graph.add_edge("node_search_embedding_hyde", "node_rrf")
        self._graph.add_edge("node_web_search_mcp", "node_rrf")

        self._graph.add_edge("node_rrf", "node_rerank")
        self._graph.add_edge("node_rerank", "node_answer_output")
        self._graph.add_edge("node_answer_output", END)

    @property
    def graph(self):
        if not self._compiled_graph:
            self._compiled_graph = self._graph.compile()
            logger.info(f"\n{self._compiled_graph.get_graph().draw_ascii()}")
        return self._compiled_graph

    def run(self, initial_state: QueryGraphState, stream: bool = False) -> QueryGraphState:
        if stream:
            return self.graph.stream(initial_state)
        else:
            return self.graph.invoke(initial_state)