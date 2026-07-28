"""SQLModel database tables: Game, Move, Log."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
    is_completed: bool = Field(default=False, index=True)
    result: Optional[str] = Field(default=None)  # "1-0", "0-1", "1/2-1/2", "*"
    is_favorite: bool = Field(default=False)
    current_fen: str = Field(default=STARTING_FEN)
    pgn: str = Field(default="")
    # Which color the human plays in this game ("white" | "black"). White
    # always moves first (chess rule); who OWNS white is decided per game.
    # Only meaningful for mode="agent".
    user_color: str = Field(default="white")

    # "agent" (vs AI), "local" (two players, one screen) or "online"
    # (two players, each with their own link).
    mode: str = Field(default="agent", index=True)
    white_name: Optional[str] = Field(default=None)
    black_name: Optional[str] = Field(default=None)
    # Per-seat secrets for online games; the invite link carries the free
    # seat's token. Never exposed in general listings.
    white_token: Optional[str] = Field(default=None)
    black_token: Optional[str] = Field(default=None)

    moves: List["Move"] = Relationship(back_populates="game")
    logs: List["Log"] = Relationship(back_populates="game")


class Move(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    move_number: int  # ply number, starting at 1
    from_square: str  # e.g. "e2"
    to_square: str    # e.g. "e4"
    move_san: str     # e.g. "e4", "Nxd5", "O-O"

    game: Optional[Game] = Relationship(back_populates="moves")


class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: Optional[int] = Field(default=None, foreign_key="game.id", index=True, nullable=True)
    timestamp: datetime = Field(default_factory=utcnow, nullable=False)
    action_type: str = Field(index=True)  # game_start | resume | move | favorite_toggle | game_over
    details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    game: Optional[Game] = Relationship(back_populates="logs")
