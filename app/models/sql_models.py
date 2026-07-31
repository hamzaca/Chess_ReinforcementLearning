"""SQLModel database tables: Game, Move, Log, AgentMemory, OpeningBookEntry."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
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


class AgentMemory(SQLModel, table=True):
    """The LLM agent's working memory: one row per agent move.

    `plan` is the agent's own rolling strategic plan; the latest row's plan
    plus the last few reasonings are fed back into the next prompt so the
    agent plays coherently across moves (and across server restarts).
    """

    __tablename__ = "agent_memory"

    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    move_number: int  # ply number of the agent move this row belongs to
    plan: str = Field(default="")
    reasoning: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class OpeningBookEntry(SQLModel, table=True):
    """Self-built opening book: positions from games the agent won.

    Keyed by the FEN with move clocks stripped (first 4 fields), so the same
    position reached by transposition maps to one entry. Consulted as a hint
    in the LLM prompt, never as a forced move.
    """

    __tablename__ = "opening_book"
    __table_args__ = (UniqueConstraint("position_fen", "move_san", name="uq_book_position_move"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    position_fen: str = Field(index=True)  # FEN without halfmove/fullmove clocks
    move_san: str
    wins: int = Field(default=0)
    losses: int = Field(default=0)


class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: Optional[int] = Field(default=None, foreign_key="game.id", index=True, nullable=True)
    timestamp: datetime = Field(default_factory=utcnow, nullable=False)
    action_type: str = Field(index=True)  # game_start | resume | move | favorite_toggle | game_over
    details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    game: Optional[Game] = Relationship(back_populates="logs")
