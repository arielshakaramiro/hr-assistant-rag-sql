"""Application settings, read from environment variables (never hardcode secrets)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: one app role (read/write) and one read-only role for the SQL agent.
    database_url: str = "postgresql+psycopg://hr:hr@localhost:5433/hr"
    database_url_ro: str = "postgresql+psycopg://hr_ro:hr_ro@localhost:5433/hr"

    # Session signing.
    session_secret: str = "dev-only-change-me"
    session_ttl_hours: int = 12
    # Secure cookie requires HTTPS. True in the deployed demo; set false for local http dev/tests.
    cookie_secure: bool = True
    # Set in production to fail fast if the session secret was left at the dev default.
    require_strong_secret: bool = False

    def validate_production(self) -> None:
        """Called at startup in production (REQUIRE_STRONG_SECRET=true) to refuse a dev secret."""
        if self.require_strong_secret and self.session_secret == "dev-only-change-me":
            raise RuntimeError("SESSION_SECRET is still the dev default — set a strong secret.")

    # LLM: any OpenAI-compatible endpoint.
    # Local default = Ollama (qwen2.5); prod = Groq (Llama 3.3 70B).
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"  # Ollama ignores it; Groq needs a real key in the env.
    llm_model: str = "qwen2.5:7b"
    llm_temperature: float = 0.0

    # Embeddings: local sentence-transformers (no API, nothing leaves).
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # Spend / abuse controls.
    daily_query_cap: int = 500  # a cap of 0 is the stop switch
    per_session_minute_cap: int = 20
    retrieval_min_score: float = 0.35  # below this, POLICY abstains (AI_QUALITY.md)
    sql_row_limit: int = 200
    sql_timeout_ms: int = 3000


settings = Settings()
