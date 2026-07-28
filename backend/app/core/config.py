from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Enterprise AI Document Intelligence Platform"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docintel"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Storage
    storage_root: str = "./storage"
    max_upload_size_mb: int = 500
    allowed_upload_mime_types: list[str] = ["application/pdf"]

    # Provider selection (swap via env — factories read these)
    llm_provider: Literal["gemini", "openai", "claude", "llama"] = "gemini"
    embedding_provider: Literal["bge_m3", "jina", "voyage", "openai"] = "bge_m3"
    reranker_provider: Literal["bge", "cohere"] = "bge"
    vectorstore_provider: Literal["qdrant", "chroma", "pinecone"] = "qdrant"

    # Gemini (live)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Stub providers (Phase 2 — keys read but adapters not implemented yet)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llama_base_url: str = ""
    jina_api_key: str = ""
    voyage_api_key: str = ""
    cohere_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_environment: str = ""

    # Embeddings (live)
    bge_m3_model_name: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024

    # Reranker (live)
    bge_reranker_model_name: str = "BAAI/bge-reranker-v2-m3"

    # Vector store (live)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "docintel"
    chroma_persist_dir: str = "./storage/chroma"

    # Retrieval tuning
    hybrid_dense_top_k: int = 20
    hybrid_bm25_top_k: int = 20
    rerank_top_k: int = 8
    multi_query_count: int = 3
    context_token_budget: int = 6000

    # Rate limiting
    rate_limit_default: str = "60/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
