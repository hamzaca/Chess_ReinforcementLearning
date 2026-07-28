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
    user_color: Literal["white", "black"]
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None
    move_count: int


class GameStateResponse(BaseModel):
    game_id: int
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    user_color: Literal["white", "black"]
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None
    move_count: int


class NewGameRequest(BaseModel):
    # Who the human plays; omitted -> the configured default (random).
    user_color: Optional[Literal["white", "black", "random"]] = None


class UndoRequest(BaseModel):
    # How many plies (half-moves) to take back. Omit for "my last move";
    # a large number rewinds to the start of the game.
    plies: Optional[int] = Field(default=None, ge=1)


class MoveRequest(BaseModel):
    from_square: str = Field(min_length=2, max_length=2, examples=["e2"])
    to_square: str = Field(min_length=2, max_length=2, examples=["e4"])
    promotion: Optional[Literal["q", "r", "b", "n"]] = None


class MovePlayed(BaseModel):
    from_square: str
    to_square: str
    san: str
    player: str  # "User" | "Agent" | a player's name in PvP games


class MoveResponse(BaseModel):
    user_move: MovePlayed
    agent_move: Optional[MovePlayed] = None
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    user_color: Literal["white", "black"]
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None
    move_count: int


class PossibleMovesRequest(BaseModel):
    square: str = Field(min_length=2, max_length=2, examples=["e2"])
    # Omitted -> the current game vs the agent; set for PvP games.
    game_id: Optional[int] = None


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
    mode: str
    white_name: Optional[str] = None
    black_name: Optional[str] = None


# ------------------------------------------------------------ two players


class PvpCreateRequest(BaseModel):
    mode: Literal["local", "online"]
    # local: both players at one screen
    white_name: Optional[str] = None
    black_name: Optional[str] = None
    # online: the creator picks a side; the opponent joins via link
    creator_name: Optional[str] = None
    creator_color: Literal["white", "black", "random"] = "random"


class PvpCreateResponse(BaseModel):
    game_id: int
    mode: str
    your_color: Optional[Literal["white", "black"]] = None  # None for local
    token: Optional[str] = None       # your seat token (online)
    join_token: Optional[str] = None  # opponent's seat token, for the invite link


class PvpJoinRequest(BaseModel):
    token: str
    name: str = Field(min_length=1, max_length=40)


class PvpJoinResponse(BaseModel):
    game_id: int
    your_color: Literal["white", "black"]
    token: str


class LastMove(BaseModel):
    from_square: str
    to_square: str
    san: str


class PvpStateResponse(BaseModel):
    game_id: int
    mode: str
    fen: str
    turn: Literal["white", "black"]
    pgn: str
    in_check: bool
    is_game_over: bool
    result: Optional[str] = None
    move_count: int
    white_name: Optional[str] = None
    black_name: Optional[str] = None
    your_color: Optional[Literal["white", "black"]] = None  # from token, online only
    opponent_joined: bool
    last_move: Optional[LastMove] = None


class PvpMoveRequest(BaseModel):
    from_square: str = Field(min_length=2, max_length=2)
    to_square: str = Field(min_length=2, max_length=2)
    promotion: Optional[Literal["q", "r", "b", "n"]] = None
    # Online games authenticate via the X-Player-Token header, not the body.


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
