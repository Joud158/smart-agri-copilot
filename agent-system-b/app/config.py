from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Agriculture Advisor - Agent System B"
    google_api_key: str = Field(default="replace_me", alias="GOOGLE_API_KEY")
    adk_model: str = Field(default="gemini-3-flash-preview", alias="ADK_MODEL")
    session_db_path: str = Field(default="/data/agent_b_sessions.sqlite", alias="SESSION_DB_PATH")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
