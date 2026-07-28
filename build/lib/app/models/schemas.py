"""Pydantic DTOs for the REST API."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CurrentGameResponse(BaseModel):
    game_id: int
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    created: bool  # True if a brand-new game was created by this call
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None


class GameStateResponse(BaseModel):
    game_id: int
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None
    move_count: int


class MoveRequest(BaseModel):
    from_square: str = Field(min_length=2, max_length=2, examples=["e2"])
    to_square: str = Field(min_length=2, max_length=2, examples=["e4"])
    promotion: Optional[Literal["q", "r", "b", "n"]] = None


class MovePlayed(BaseModel):
    from_square: str
    to_square: str
    san: str
    player: Literal["User", "Agent"]


class MoveResponse(BaseModel):
    user_move: MovePlayed
    agent_move: Optional[MovePlayed] = None
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None


class PossibleMovesRequest(BaseModel):
    square: str = Field(min_length=2, max_length=2, examples=["e2"])


class PossibleMovesResponse(BaseModel):
    square: str
    moves: List[str]


class GameSummary(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    is_completed: bool
    result: Optional[str] = None
    is_favorite: bool
    move_count: int


class FavoriteResponse(BaseModel):
    game_id: int
    is_favorite: bool


class ReplayMove(BaseModel):
    move_number: int
    from_square: str
    to_square: str
    move_san: str
    fen_after: str


class ReplayResponse(BaseModel):
    game_id: int
    pgn: str
    start_fen: str
    moves: List[ReplayMove]


class LogEntryResponse(BaseModel):
    id: int
    game_id: Optional[int] = None
    timestamp: datetime
    action_type: str
    details: Dict[str, Any]
