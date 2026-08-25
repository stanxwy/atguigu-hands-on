from functools import lru_cache

from app.factories.infra import (
    get_doc_store,
    get_identity_repo,
    get_object_store,
    get_password_hasher,
    get_token_service,
)
from app.factories.workflows import create_ingest_workflow, create_query_workflow
from app.services.auth_service import AuthService
from app.services.ingestion_service import IngestionService
from app.services.org_service import OrgService
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


@lru_cache
def create_auth_service() -> AuthService:
    return AuthService(
        identity_repo=get_identity_repo(),
        token_service=get_token_service(),
        password_hasher=get_password_hasher(),
    )


@lru_cache
def create_org_service() -> OrgService:
    return OrgService(
        identity_repo=get_identity_repo(),
        password_hasher=get_password_hasher(),
    )