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
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5"

    # Online PvP invite links expire if unclaimed for this long.
    invite_ttl_hours: int = 24


settings = Settings()
