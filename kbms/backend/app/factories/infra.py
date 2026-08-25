from functools import lru_cache

from app.domain.ports.doc_store import DocumentStore
from app.domain.ports.embedder import Embedder
from app.domain.ports.llm import LLMPort
from app.domain.ports.object_store import ObjectStore
from app.domain.ports.pdf_parser import PDFParser
from app.domain.ports.reranker import Reranker
from app.domain.ports.vector_db import ChunksVectorDB, ItemNameVectorDB
from app.domain.ports.web_search import WebSearch
from app.infra.config.settings import Settings, get_settings
from app.infra.external.embedder.bge_m3 import BgeM3Embedding
from app.infra.external.llm.dashscope import DashScopeService
from app.infra.external.mcp_search import MCPSearchService
from app.infra.external.mineru import MineruService
from app.infra.external.reranker.dashscope import DashScopeReranker
from app.infra.persistence.milvus import (
    ChunksMilvusService,
    ItemNameMilvusService,
)
from app.infra.persistence.minio import MinIOService
from app.infra.persistence.mongo import MongoService


@lru_cache(maxsize=1)
def get_object_store(settings: Settings | None = None) -> ObjectStore:
    settings = settings or get_settings()
    return MinIOService(settings)


@lru_cache(maxsize=1)
def get_item_name_vector_db(settings: Settings | None = None) -> ItemNameVectorDB:
    settings = settings or get_settings()
    return ItemNameMilvusService(settings, get_embedder())


@lru_cache(maxsize=1)
def get_chunks_vector_db(settings: Settings | None = None) -> ChunksVectorDB:
    settings = settings or get_settings()
    return ChunksMilvusService(settings, get_embedder())


@lru_cache(maxsize=1)
def get_doc_store(settings: Settings | None = None) -> DocumentStore:
    settings = settings or get_settings()
    return MongoService(settings)





@lru_cache(maxsize=1)
def get_reranker(settings: Settings | None = None) -> Reranker:
    settings = settings or get_settings()
    return DashScopeReranker(settings)


@lru_cache(maxsize=1)
def get_llm_service(settings: Settings | None = None) -> LLMPort:
    settings = settings or get_settings()
    return DashScopeService(settings)


@lru_cache(maxsize=1)
def get_pdf_parser(settings: Settings | None = None) -> PDFParser:
    settings = settings or get_settings()
    return MineruService(settings)


@lru_cache(maxsize=1)
def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    return BgeM3Embedding(settings)


@lru_cache(maxsize=1)
def get_mcp_search_service(settings: Settings | None = None) -> WebSearch:
    settings = settings or get_settings()
    return MCPSearchService(settings)
