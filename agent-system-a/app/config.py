from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration.

    Using a settings class keeps environment handling explicit, testable,
    and easier to explain during the presentation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Agriculture Advisor - Agent System A"
    request_timeout_seconds: int = Field(default=20, alias="REQUEST_TIMEOUT_SECONDS")

    openai_api_key: str = Field(default="replace_me", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    qdrant_url: str = Field(default="http://vector-db:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="smart_agri_docs", alias="QDRANT_COLLECTION")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    top_k: int = Field(default=4, alias="TOP_K")
    rag_chunk_size: int = Field(default=650, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=120, alias="RAG_CHUNK_OVERLAP")

    agent_b_url: str = Field(default="http://agent-system-b:8102", alias="AGENT_B_URL")
    mcp_server_url: str = Field(default="http://mcp-server:8103", alias="MCP_SERVER_URL")

    session_db_path: str = Field(default="/data/sessions.sqlite", alias="SESSION_DB_PATH")
    allow_out_of_domain: bool = Field(default=False, alias="ALLOW_OUT_OF_DOMAIN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings so the app does not repeatedly parse environment values."""

    return Settings()
