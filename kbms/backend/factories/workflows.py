from functools import lru_cache

from app.factories.infra import (
    get_chunks_vector_db,
    get_doc_store,
    get_embedder,
    get_item_name_vector_db,
    get_llm_service,
    get_mcp_search_service,
    get_object_store,
    get_pdf_parser,
    get_reranker,
)
from app.workflows.ingestion.main_graph import KBImportWorkflow
from app.workflows.ingestion.nodes.node_bge_embedding import NodeBGEEmbedding
from app.workflows.ingestion.nodes.node_document_split import NodeDocumentSplit
from app.workflows.ingestion.nodes.node_entry import NodeEntry
from app.workflows.ingestion.nodes.node_import_milvus import NodeImportMilvus
from app.workflows.ingestion.nodes.node_item_name_recognition import (
    NodeItemNameRecognition,
)
from app.workflows.ingestion.nodes.node_md_img import NodeMDImg
from app.workflows.ingestion.nodes.node_pdf_to_md import NodePDFToMD
from app.workflows.query.main_graph import KBQueryWorkflow
from app.workflows.query.nodes.node_answer_output import NodeAnswerOutput
from app.workflows.query.nodes.node_item_name_confirm import NodeItemNameConfirm
from app.workflows.query.nodes.node_rerank import NodeRerank
from app.workflows.query.nodes.node_rrf import NodeRrf
from app.workflows.query.nodes.node_search_embedding import NodeSearchEmbedding
from app.workflows.query.nodes.node_search_embedding_hyde import NodeSearchEmbeddingHyde
from app.workflows.query.nodes.node_web_search_mcp import NodeWebSearchMcp


@lru_cache
def create_ingest_workflow():
    # infra / services
    pdf_parser = get_pdf_parser()
    llm_service = get_llm_service()
    object_store = get_object_store()
    embedder = get_embedder()
    item_name_vector_db = get_item_name_vector_db()
    chunks_vector_db = get_chunks_vector_db()

    # nodes
    node_entry = NodeEntry()
    node_pdf_to_md = NodePDFToMD(pdf_parser)
    node_md_img = NodeMDImg(llm_service, object_store)
    node_document_split = NodeDocumentSplit()
    node_item_name_recognition = NodeItemNameRecognition(llm_service, embedder, item_name_vector_db)
    node_bge_embedding = NodeBGEEmbedding(embedder)
    node_import_milvus = NodeImportMilvus(chunks_vector_db)

    return KBImportWorkflow(
        node_entry=node_entry,
        node_pdf_to_md=node_pdf_to_md,
        node_md_img=node_md_img,
        node_document_split=node_document_split,
        node_item_name_recognition=node_item_name_recognition,
        node_bge_embedding=node_bge_embedding,
        node_import_milvus=node_import_milvus
    )
    

@lru_cache
def create_query_workflow() -> KBQueryWorkflow:
    # infra / services
    llm = get_llm_service()
    doc_store = get_doc_store()
    item_name_vectordb = get_item_name_vector_db()
    chunks_vector_db = get_chunks_vector_db()
    web_search = get_mcp_search_service()
    reranker = get_reranker()

    # nodes
    node_item_name_confirm = NodeItemNameConfirm(doc_store, llm, item_name_vectordb)
    node_search_embedding = NodeSearchEmbedding(chunks_vector_db)
    node_search_embedding_hyde = NodeSearchEmbeddingHyde(llm, chunks_vector_db)
    node_web_search_mcp = NodeWebSearchMcp(web_search)
    node_rrf = NodeRrf()
    node_rerank = NodeRerank(reranker)
    node_answer_output = NodeAnswerOutput(doc_store, llm)

    return KBQueryWorkflow(
        node_item_name_confirm=node_item_name_confirm,
        node_search_embedding=node_search_embedding,
        node_search_embedding_hyde=node_search_embedding_hyde,
        node_web_search_mcp=node_web_search_mcp,
        node_rrf=node_rrf,
        node_rerank=node_rerank,
        node_answer_output=node_answer_output
    )