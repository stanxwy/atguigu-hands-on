from app.factories.services import create_ingestion_service, create_query_service
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService


def get_ingestion_service() -> IngestionService:
    return create_ingestion_service()


def get_query_service() -> QueryService:
    return create_query_service()
