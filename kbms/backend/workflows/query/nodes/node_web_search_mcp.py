import asyncio
import json

from app.domain.ports.web_search import WebSearch
from app.workflows.query.base import NodeBase
from app.workflows.query.state import QueryGraphState


class NodeWebSearchMcp(NodeBase):

    name: str = "node_web_search_mcp"

    def __init__(self, mcp: WebSearch):
        super().__init__()
        self._mcp = mcp
    
    def process(self, state: QueryGraphState) -> QueryGraphState:
        query = state.get("rewritten_query", "")
        docs = []
        if query:
            result = asyncio.run(self._mcp.search_web(query))
            if result:
                pages = json.loads(result.content[0].text).get("pages") or []
                docs = [{
                    "snippet": (page.get("snippet") or "").strip(),
                    "url": (page.get("url") or "").strip(),
                    "title": (page.get("title") or "").strip()
                } for page in pages if page.get("snippet")]
                self.logger.info(f"MCP search result: \n{json.dumps(docs, indent=2, ensure_ascii=False)}")

        return { "web_search_docs": docs }