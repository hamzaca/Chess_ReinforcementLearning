"""SQLModel engine and session management."""

from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite needs check_same_thread=False because FastAPI may service a request
# from a different thread than the one that created the connection.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, echo=settings.sql_echo, connect_args=_connect_args)


def init_db() -> None:
    """Create all tables. Idempotent — used for dev/test bootstrap; real
    schema evolution is handled by alembic migrations."""
    # Import models so their tables are registered on SQLModel.metadata.
    from app.models import sql_models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    with Session(engine) as session:
        yield session
