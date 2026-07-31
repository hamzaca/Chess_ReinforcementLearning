"""Application configuration.

All values can be overridden through environment variables (or a `.env`
file), e.g. ``DATABASE_URL=postgresql+psycopg://user:pass@db:5432/chess``
to swap SQLite for PostgreSQL without touching code.
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # sqlite for local development; swap via env var for PostgreSQL.
    database_url: str = "sqlite:///./chess_data.db"
    sql_echo: bool = False

    # CORS origins for the Angular dev server / deployed frontend.
    cors_origins: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
    ]

    # Search depth for the minimax chess agent (plies).
    agent_depth: int = 2

    # Which color the human plays in a new game: "white" | "black" | "random".
    default_user_color: str = "random"

    # Agent backend: "auto" (LLM when an API key is configured, else minimax),
    # "minimax", or "llm".
    agent_backend: str = "auto"

    # Claude API key for the LLM agent — set it in .env (never commit it).
    # Also sent as the bearer token to `llm_base_url` when that is set.
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5"

    # OpenAI-compatible server for the LLM agent (include the /v1 suffix,
    # e.g. a local proxy . The default is Anthropic's
    # own OpenAI-compatible endpoint, so an ANTHROPIC_API_KEY alone works.
    llm_base_url: str = "https://api.anthropic.com/v1/"

    # LLM robustness knobs: total move attempts (1 initial + N-1 retries with
    # error feedback) before falling back to minimax, and the per-request
    # timeout in seconds.
    max_llm_attempts: int = 3
    request_timeout_s: float = 30.0

    # Online PvP invite links expire if unclaimed for this long.
    invite_ttl_hours: int = 24


settings = Settings()
