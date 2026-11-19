"""Configurações lidas do arquivo .env (nunca coloque segredos no código)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"
    app_name: str = "Ísis"
    frontend_origin: str = "http://localhost:5173"
    timezone_default: str = "America/Sao_Paulo"

    # Etapa 1B — preenchidos no .env
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    llm_provider: str = "opencode-go"
    llm_base_url: str = "https://opencode.ai/inference/go/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-6-luna"
    llm_api_style: str = "responses"


@lru_cache
def get_settings() -> Settings:
    return Settings()
