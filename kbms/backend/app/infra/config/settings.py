from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    APP_NAME: str = "Knowledge Base RAG"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    # 统一新路由前缀（SPEC §3.1/§5.2）；旧 /api/v1 保留为兼容变量。
    API_STR: str = "/api"
    BACKEND_CORS_ORIGINS: list[str] = ["*"] # ["http://localhost:8000"]
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ===== Environment =====
    env: str = Field("prod", env="APP_ENV")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # ===== LLM =====
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_api_base: str = Field("https://api.openai.com/v1", env="OPENAI_API_BASE")
    llm_default_model: str = Field(..., env="LLM_DEFAULT_MODEL")
    vl_model: str = Field(..., env="VL_MODEL")
    item_model: str = Field(..., env="ITEM_MODEL")
    llm_temperature: float = Field(0.8, env="LLM_DEFAULT_TEMPERATURE")

    # ===== Embedding =====
    bge_m3_path: str = Field(..., env="BGE_M3_PATH")
    bge_m3: str = Field("BAAI/bge-m3", env="BGE_M3")
    bge_device: str = Field("cuda:0", env="BGE_DEVICE")
    bge_fp16: bool = Field(True, env="BGE_FP16")

    # ===== Reranker REMOTE =====
    @property
    def text_rerank_api_key(self) -> str:
        return self.openai_api_key
    text_rerank_model: str = Field(..., env="TEXT_RERANK_MODEL")
    text_rerank_instruct: str | None = Field(None, env="TEXT_RERANK_INSTRUCT")

    # ===== Reranker Local =====
    bge_rerank_model: str = Field("", env="BGE_RERANKER_LARGE")
    bge_rerank_device: str = Field("cuda:0", env="BGE_RERANKER_DEVICE")
    bge_rerank_fp16: bool = Field(True, env="BGE_RERANKER_FP16")

    # ===== MCP / DashScope =====
    mcp_dashscope_base_url: str = Field(..., env="MCP_DASHSCOPE_BASE_URL")
    @property
    def mcp_dashscope_api_key(self) -> str:
        return self.openai_api_key

    # ===== Milvus =====
    milvus_url: str = Field(..., env="MILVUS_URL")
    chunks_collection: str = Field(..., env="CHUNKS_COLLECTION")
    item_name_collection: str = Field(..., env="ITEM_NAME_COLLECTION")

    # ===== Mineru =====
    mineru_base_url: str = Field(..., env="MINERU_BASE_URL")
    mineru_api_token: str = Field(..., env="MINERU_API_TOKEN")

    # ===== MinIO =====
    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")
    minio_secure: bool = Field(False, env="MINIO_SECURE")
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(..., env="MINIO_BUCKET_NAME")
    minio_img_dir: str = Field("", env="MINIO_IMG_DIR")

    # ===== MongoDB =====
    mongo_url: str = Field(..., env="MONGO_URL")
    mongo_db_name: str = Field(..., env="MONGO_DB_NAME")

    # ===== PostgreSQL / Relational DB (KBMS) =====
    # SQLite is the dev/test default (no extra dependency); switch to
    # postgresql+psycopg://... in production via the DATABASE_URL env var.
    DATABASE_URL: str = Field("sqlite:///./kbms.db", env="DATABASE_URL")

    # ===== Auth / JWT =====
    JWT_SECRET: str = Field("kbms-dev-secret-change-me", env="JWT_SECRET")
    JWT_EXPIRE_MINUTES: int = Field(1440, env="JWT_EXPIRE_MINUTES")

    # ===== Data Permission =====
    DATA_PERM_DEPT_RECURSIVE: bool = Field(True, env="DATA_PERM_DEPT_RECURSIVE")

    # ===== FAQ / Gap thresholds =====
    FAQ_SIMILARITY_THRESHOLD: float = Field(0.85, env="FAQ_SIMILARITY_THRESHOLD")
    FAQ_MIN_FREQUENCY: int = Field(3, env="FAQ_MIN_FREQUENCY")
    GAP_SIMILARITY_THRESHOLD: float = Field(0.5, env="GAP_SIMILARITY_THRESHOLD")

    class Config:
        env_file = ".env"
        env_prefix = "" # env_prefix = "KB_"
        # 忽略 .env 中未在 Settings 声明的键（如 DATA_BASED_ROOT_DIR、EMBEDDING_DIM、
        # MODELSCOPE_CACHE、NVIDIA_API_KEY 等被旧代码通过 os.getenv 读取的变量），
        # 否则 pydantic v2 默认 extra="forbid" 会在实例化时抛 ValidationError。
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()