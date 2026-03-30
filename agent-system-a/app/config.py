from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration for Agent System A."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Agriculture Advisor - Agent System A"
    request_timeout_seconds: int = Field(default=20, alias="REQUEST_TIMEOUT_SECONDS")
    service_retry_attempts: int = Field(default=2, alias="SERVICE_RETRY_ATTEMPTS")
    service_retry_backoff_ms: int = Field(default=250, alias="SERVICE_RETRY_BACKOFF_MS")

    llm_provider: str = Field(default="none", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="replace_me", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:1.5b", alias="OLLAMA_MODEL")
    ollama_vision_model: str = Field(default="gemma3:4b-it-qat", alias="OLLAMA_VISION_MODEL")
    enable_react_agent: bool = Field(default=False, alias="ENABLE_REACT_AGENT")
    enable_llm_synthesis: bool = Field(default=False, alias="ENABLE_LLM_SYNTHESIS")
    agent_pattern: str = Field(default="deterministic", alias="AGENT_PATTERN")
    max_tool_steps: int = Field(default=4, alias="MAX_TOOL_STEPS")

    enable_web_search: bool = Field(default=True, alias="ENABLE_WEB_SEARCH")
    enable_query_translation_fallback: bool = Field(default=False, alias="ENABLE_QUERY_TRANSLATION_FALLBACK")
    enable_vision_ingestion: bool = Field(default=False, alias="ENABLE_VISION_INGESTION")

    qdrant_url: str = Field(default="http://vector-db:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="smart_agri_docs", alias="QDRANT_COLLECTION")
    embedding_provider: str = Field(default="local_deterministic", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="local-deterministic-v2", alias="EMBEDDING_MODEL")
    local_embedding_dimension: int = Field(default=256, alias="LOCAL_EMBEDDING_DIMENSION")
    reranker_mode: str = Field(default="hybrid_lexical", alias="RERANKER_MODE")

    top_k: int = Field(default=5, alias="TOP_K")
    rag_fetch_k: int = Field(default=12, alias="RAG_FETCH_K")
    rag_chunk_size: int = Field(default=900, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=180, alias="RAG_CHUNK_OVERLAP")
    max_specialist_steps: int = Field(default=6, alias="MAX_SPECIALIST_STEPS")

    agent_b_url: str = Field(default="http://agent-system-b:8102", alias="AGENT_B_URL")
    mcp_server_url: str = Field(default="http://mcp-server:8103", alias="MCP_SERVER_URL")
    mcp_streamable_http_path: str = Field(default="/mcp", alias="MCP_STREAMABLE_HTTP_PATH")
    enable_mcp_client: bool = Field(default=True, alias="ENABLE_MCP_CLIENT")

    session_db_path: str = Field(default="/data/sessions.sqlite", alias="SESSION_DB_PATH")
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")
    allow_out_of_domain: bool = Field(default=False, alias="ALLOW_OUT_OF_DOMAIN")
    allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="ALLOWED_ORIGINS")
    admin_api_token: str = Field(default="", alias="ADMIN_API_TOKEN")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def mcp_streamable_http_url(self) -> str:
        return f"{self.mcp_server_url.rstrip('/')}{self.mcp_streamable_http_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
