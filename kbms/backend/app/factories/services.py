from functools import lru_cache

from app.factories.infra import get_doc_store, get_object_store
from app.factories.workflows import create_ingest_workflow, create_query_workflow
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService


@lru_cache
def create_ingestion_service() -> IngestionService:
    return IngestionService(
        object_store=get_object_store(),
        workflow=create_ingest_workflow(),
    )

@lru_cache
def create_query_service() -> QueryService:
    return QueryService(
        doc_store=get_doc_store(),
        workflow=create_query_workflow(),
    )