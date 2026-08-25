import json
import logging

from pymilvus import AnnSearchRequest, DataType, MilvusClient, WeightedRanker

from app.domain.ports.embedder import Embedder
from app.domain.ports.vector_db import ChunksVectorDB, ItemNameVectorDB, VectorDB
from app.infra.config.settings import Settings
from app.workflows.ingestion.exceptions import VectorDBError

logger = logging.getLogger(__name__)

VARCHAR_MAX_LENGTH = 100
VECTOR_DIMENSION_DEFAULT = 1024

RANKER_WEIGHTS = (0.8, 0.2)
ITEM_NAME_SEARCH_LIMIT = 5
CHUNK_SEARCH_LIMIT = 10

class MilvusService(VectorDB):
    def __init__(self, settings: Settings, embedding_service: Embedder):
        self._milvus_config = settings
        self._milvus_client = None
        self._embedding_service = embedding_service

    def _escape_milvus_string(self, value: str) -> str:
        """
        Milvus数据库过滤表达式中字符串的安全转义函数（防止解析失败）
        """
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
        return value

    def _get_milvus_client(self):
        if self._milvus_client is None:
            self._milvus_client = MilvusClient(self._milvus_config.milvus_url)
        return self._milvus_client
    
    def _create_hybrid_search_requests(self, dense_vector, sparse_vector, dense_params=None, sparse_params=None, expr=None, limit=5):
        if dense_params is None:
            dense_params = {"metric_type": "COSINE"}
        if sparse_params is None:
            sparse_params = {"metric_type": "IP"}

        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field="dense_vector",
            param=dense_params,
            expr=expr,
            limit=limit
        )
        sparse_req = AnnSearchRequest(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param=sparse_params,
            expr=expr,
            limit=limit
        )
        return [dense_req, sparse_req]

    def _hybrid_search(self, collection_name, reqs, ranker_weights=(0.5, 0.5), norm_score=False, limit=5, output_fields=None, search_params=None):
        try:
            rerank = WeightedRanker(ranker_weights[0], ranker_weights[1], norm_score=norm_score)
            if output_fields is None:
                output_fields = ["item_name"]

            res = self._get_milvus_client().hybrid_search(
                collection_name=collection_name,
                reqs=reqs,
                ranker=rerank,
                limit=limit,
                output_fields=output_fields,
                search_params=search_params
            )
            logger.info(f"Hybrid searching collection [{collection_name}] found {len(res[0])} results")
            return res
        except Exception as e:
            logger.exception(f"Error hybrid searching collection [{collection_name}]: {e!s}", stack_info=True)
            return None


class ItemNameMilvusService(MilvusService, ItemNameVectorDB):

    def create_collection(self, vector_dimension: int = VECTOR_DIMENSION_DEFAULT):
        # enable_dynamic_field=True：allow insertion of records with fields not defined in schema
        milvus_client = self._get_milvus_client()
        collection_name = self._milvus_config.item_name_collection
        if milvus_client.has_collection(collection_name):
            logger.info(f"Collection {collection_name} already exists, skip creating...")
            return

        schema = milvus_client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="file_title", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="item_name", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dimension)
        schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

        index_params = milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_name="dense_vector_index",
            index_type="IVF_FLAT",  # good compatibility for small dataset
            metric_type="COSINE",   # similarity metric: Cosine
            params={"nlist": 128}   # number of clusters, affects precision and speed
        )

        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_vector_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",       # similarity metric: Inner Product
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "normalize": True,
                "quantization": "none"
                # disable quantization: no compression since BGE_FP16=1 is used for generating vectors
                # "quantization": "none" save original vector without compression
                # "quantization": "sq8"  save compressed vector
            })

        milvus_client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )

    def insert_data(self, data: list[dict]):
        result = self._get_milvus_client().insert(collection_name=self._milvus_config.item_name_collection, data=data)
        logger.info(f"Inserted count {result.get('insert_count', 0)}")
        return result

    def delete_data_by_file_title(self, file_title: str):
        try:
            safe_file_title = self._escape_milvus_string(file_title)
            result = self._get_milvus_client().delete(collection_name=self._milvus_config.item_name_collection, filter=f'file_title=="{safe_file_title}"')
            logger.debug(f"Deleted count {result.get('delete_count', 0)}")
            return result
        except Exception as e:
            logger.error(f"Error deleting data from vector db: {str(e)}")
            raise VectorDBError(f"Error deleting data from vector db: {str(e)}")

    def hybrid_search_item_name(self, item_names: list[str]) -> list[dict]:
        results = []
        # generate embeddings for all item names for better performance
        embeddings = self._embedding_service.generate_embeddings(item_names)

        # traverse all item names, do vector search one by one 
        # to make sure the results match the original item names
        for i, item_name in enumerate(item_names):
            try:
                # [0.12, 0.35,...]
                dense_vector = embeddings.get("dense")[i]
                # {100:0.747, 205:0.664}
                sparse_vector = embeddings.get("sparse")[i]
                reqs = self._create_hybrid_search_requests(
                    dense_vector=dense_vector,
                    sparse_vector=sparse_vector,
                    limit=ITEM_NAME_SEARCH_LIMIT
                )
                search_res = self._hybrid_search(
                    collection_name=self._milvus_config.item_name_collection,
                    reqs=reqs,
                    ranker_weights=RANKER_WEIGHTS,
                    limit=ITEM_NAME_SEARCH_LIMIT,
                    norm_score=True,
                    output_fields=["item_name"]
                )
                logger.info(f"Keyword [{item_name}] search result in vector db: \n{json.dumps(search_res, ensure_ascii=False, indent=4)}")

                matches = [
                    {
                        "item_name": hit.get("entity", {}).get("item_name"),
                        "score": hit.get("distance"),
                        # hit: {"id", "distance": score, "entity": {"item_name"}}
                    } for hit in (search_res[0] if search_res and len(search_res) > 0 else [])
                ]
                results.append({
                    "resolved_name": item_name,
                    "matches": matches
                })
            except Exception as e:
                logger.exception(f"Error searching item name '{item_name}': {e!s}", stack_info=True)
        return results


class ChunksMilvusService(MilvusService, ChunksVectorDB):

    def create_collection(self, vector_dimension: int = VECTOR_DIMENSION_DEFAULT):
        milvus_client = self._get_milvus_client()
        collection_name = self._milvus_config.chunks_collection
        if milvus_client.has_collection(collection_name):
            logger.warning(f"Collection {collection_name} already exists, skip creating...")
            return

        schema = milvus_client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="chunk_id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="parent_title", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="part", datatype=DataType.INT8)
        schema.add_field(field_name="file_title", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="item_name", datatype=DataType.VARCHAR, max_length=VARCHAR_MAX_LENGTH)
        schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dimension)

        index_params = milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_name="dense_vector_index",
            index_type="AUTOINDEX",
            metric_type="COSINE"
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_inverted_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            params={"inverted_index_algo": "DAAT_MAXSCORE", "normalize": True, "quantization": "none"}
        )
        milvus_client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )

    def insert_data(self, data: list[dict]):
        result = self._get_milvus_client().insert(collection_name=self._milvus_config.chunks_collection, data=data)
        logger.info(f"Inserted count {result.get('insert_count', 0)}")
        return result

    def delete_data_by_file_title(self, file_title: str):
        try:
            file_title = self._escape_milvus_string(file_title)
            result = self._get_milvus_client().delete(collection_name=self._milvus_config.chunks_collection, filter=f"file_title=='{file_title}'")
            logger.debug(f"Deleted count {result.get('delete_count', 0)}")
            return result
        except Exception as e:
            logger.exception(f"Error deleting data from vector db: {e!s}", stack_info=True)
            raise VectorDBError(f"Error deleting data from vector db: {e!s}")

    def hybrid_search_chunks(self, input_text: str, item_names: list[str]) -> list[dict]:
        try:
            embeddings = self._embedding_service.generate_embeddings([input_text])
            dense_vec = embeddings.get("dense")[0]
            sparse_vec = embeddings.get("sparse")[0]

            expr = None
            if item_names:
                #quoted = ", ".join(f'"{v}"' for v in item_names)
                #expr = f"item_name in [{quoted}]"
                # 'item_name in ["BrotherHAK-180烫金机","BrotherHAK180烫金机"]'
                expr = f'item_name in {item_names}'
                logger.info(f"Filter expression: {expr}")
            else:
                logger.info("No item name filter specified, searching all chunks...")

            reqs = self._create_hybrid_search_requests(
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
                expr=expr,
                limit=CHUNK_SEARCH_LIMIT
            )
            logger.info("searching chunks...")
            search_res = self._hybrid_search(
                collection_name=self._milvus_config.chunks_collection,
                reqs=reqs,
                ranker_weights=RANKER_WEIGHTS,
                output_fields=["chunk_id", "content", "item_name"]
            )
            return search_res[0] if search_res else []
        except Exception as e:
            logger.exception(f"Error searching chunks: {e}")
            return []