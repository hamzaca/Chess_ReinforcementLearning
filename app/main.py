"""FastAPI entry point for the Chess AI application.

White always moves first (chess rule), but which SIDE the human plays is
decided per game (random by default). The agent answers as the other color;
if the server restarts mid-exchange — or an undo lands on the agent's turn —
the agent catches up automatically.
"""

import random
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.agents.chess_agent import ChessAgent
from app.agents.llm_agent import get_chess_agent
from app.config import settings
from app.database import get_session, init_db
from app.models.schemas import (
    CurrentGameResponse,
    FavoriteResponse,
    GameStateResponse,
    GameSummary,
    LastMove,
    LogEntryResponse,
    MovePlayed,
    MoveRequest,
    MoveResponse,
    NewGameRequest,
    PossibleMovesRequest,
    PossibleMovesResponse,
    PvpCreateRequest,
    PvpCreateResponse,
    PvpJoinRequest,
    PvpJoinResponse,
    PvpMoveRequest,
    PvpStateResponse,
    ReplayResponse,
    UndoRequest,
)
from app.models.sql_models import Game, Log
from app.observability.tracer import trace
from app.services.chess_service import ChessService, IllegalMoveError
from app.services.game_manager import GameManager, get_game_manager
from app.services.replay_service import ReplayService, get_replay_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev/test bootstrap; production schema evolution goes through alembic.
    init_db()
    yield


app = FastAPI(title="Chess AI", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------- helpers


def _agent_color(game: Game) -> str:
    return "black" if game.user_color == "white" else "white"


def _agent_reply(game: Game, manager: GameManager, agent) -> Optional[MovePlayed]:
    """If it is the agent's turn in `game`, let it move. Returns the move
    played (or None). Finishes the game when the agent's move ends it."""
    status = ChessService.status(game.current_fen)
    if status["is_game_over"] or status["turn"] != _agent_color(game):
        return None

    history = [m.move_san for m in manager.moves_for(game.id)]
    with trace("agent.select_move"):
        choice = agent.select_move(game.current_fen, history_sans=history)
    if choice is None:
        return None

    outcome = ChessService.apply_move(
        game.current_fen, choice["from_square"], choice["to_square"], choice["promotion"]
    )
    manager.record_move(
        game,
        from_square=outcome["from_square"],
        to_square=outcome["to_square"],
        san=outcome["san"],
        new_fen=outcome["fen"],
        player="Agent",
    )
    if outcome["is_game_over"]:
        manager.finish_game(game, result=outcome["result"])
    return MovePlayed(
        from_square=outcome["from_square"],
        to_square=outcome["to_square"],
        san=outcome["san"],
        player="Agent",
    )


def _state_of(game: Game, manager: GameManager) -> GameStateResponse:
    status = ChessService.status(game.current_fen)
    return GameStateResponse(
        game_id=game.id,
        fen=game.current_fen,
        turn=status["turn"],
        pgn=game.pgn,
        user_color=game.user_color,
        in_check=status["in_check"],
        is_game_over=game.is_completed or status["is_game_over"],
        result=game.result if game.is_completed else status["result"],
        move_count=manager.move_count(game.id),
    )


def _current_response(game: Game, manager: GameManager, created: bool) -> CurrentGameResponse:
    state = _state_of(game, manager)
    return CurrentGameResponse(created=created, **state.model_dump())


# ------------------------------------------------------------------- games


@app.get("/api/games/current", response_model=CurrentGameResponse)
def get_current_game(
    manager: GameManager = Depends(get_game_manager),
    agent=Depends(get_chess_agent),
):
    """Most recent unfinished game; creates one if none exists."""
    game, created = manager.get_or_create_current()
    # Catch up if it's the agent's turn (agent plays white, restart, undo...).
    _agent_reply(game, manager, agent)
    return _current_response(game, manager, created)


@app.post("/api/games/new", response_model=CurrentGameResponse)
def new_game(
    request: Optional[NewGameRequest] = None,
    manager: GameManager = Depends(get_game_manager),
    agent=Depends(get_chess_agent),
):
    """Complete the current game and start a fresh one (random side default)."""
    user_color = request.user_color if request else None
    game = manager.start_new_game(user_color=user_color)
    # When the agent got white, it opens the game immediately.
    _agent_reply(game, manager, agent)
    return _current_response(game, manager, created=True)


@app.get("/api/games", response_model=List[GameSummary])
def list_games(
    favorites_only: bool = Query(default=False),
    manager: GameManager = Depends(get_game_manager),
):
    return [
        GameSummary(
            id=g.id,
            created_at=g.created_at,
            updated_at=g.updated_at,
            is_completed=g.is_completed,
            result=g.result,
            is_favorite=g.is_favorite,
            move_count=manager.move_count(g.id),
            mode=g.mode,
            white_name=g.white_name,
            black_name=g.black_name,
        )
        for g in manager.list_games(favorites_only=favorites_only)
    ]


@app.post("/api/games/{game_id}/favorite", response_model=FavoriteResponse)
def toggle_favorite(game_id: int, manager: GameManager = Depends(get_game_manager)):
    game = manager.toggle_favorite(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    return FavoriteResponse(game_id=game.id, is_favorite=game.is_favorite)


@app.get("/api/games/{game_id}/replay", response_model=ReplayResponse)
def get_replay(game_id: int, replay: ReplayService = Depends(get_replay_service)):
    response = replay.get_replay(game_id)
    if response is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    return response


# -------------------------------------------------------------- game play


@app.get("/api/game-state", response_model=GameStateResponse)
def game_state(manager: GameManager = Depends(get_game_manager)):
    game, _ = manager.get_or_create_current()
    return _state_of(game, manager)


@app.post("/api/move", response_model=MoveResponse)
def make_move(
    request: MoveRequest,
    manager: GameManager = Depends(get_game_manager),
    agent=Depends(get_chess_agent),
):
    game, _ = manager.get_or_create_current()
    if game.is_completed:
        raise HTTPException(status_code=409, detail="Game is already over. Start a new game.")

    status = ChessService.status(game.current_fen)
    if status["is_game_over"]:
        raise HTTPException(status_code=409, detail="Game is already over. Start a new game.")
    if status["turn"] != game.user_color:
        raise HTTPException(status_code=409, detail="It is not your turn.")

    try:
        outcome = ChessService.apply_move(
            game.current_fen, request.from_square, request.to_square, request.promotion
        )
    except IllegalMoveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    manager.record_move(
        game,
        from_square=outcome["from_square"],
        to_square=outcome["to_square"],
        san=outcome["san"],
        new_fen=outcome["fen"],
        player="User",
    )
    user_move = MovePlayed(
        from_square=outcome["from_square"],
        to_square=outcome["to_square"],
        san=outcome["san"],
        player="User",
    )

    agent_move: Optional[MovePlayed] = None
    if outcome["is_game_over"]:
        manager.finish_game(game, result=outcome["result"])
    else:
        agent_move = _agent_reply(game, manager, agent)

    final_status = ChessService.status(game.current_fen)
    return MoveResponse(
        user_move=user_move,
        agent_move=agent_move,
        fen=game.current_fen,
        turn=final_status["turn"],
        pgn=game.pgn,
        user_color=game.user_color,
        in_check=final_status["in_check"],
        is_game_over=game.is_completed or final_status["is_game_over"],
        result=game.result if game.is_completed else final_status["result"],
        move_count=manager.move_count(game.id),
    )


@app.post("/api/undo", response_model=GameStateResponse)
def undo_move(
    request: Optional[UndoRequest] = None,
    manager: GameManager = Depends(get_game_manager),
    agent=Depends(get_chess_agent),
):
    """Take back the user's last move — or many plies, back to the start."""
    game = manager.get_current_game()
    if game is None:
        raise HTTPException(status_code=409, detail="No game in progress.")

    plies = request.plies if request else None
    if manager.undo_moves(game, plies=plies) is None:
        raise HTTPException(status_code=409, detail="Nothing to undo.")

    # If the rewind landed on the agent's turn (user plays black, undo to
    # start), the agent replays its move so the user is always to move.
    _agent_reply(game, manager, agent)
    return _state_of(game, manager)


@app.post("/api/possible-moves", response_model=PossibleMovesResponse)
def possible_moves(
    request: PossibleMovesRequest,
    manager: GameManager = Depends(get_game_manager),
):
    if request.game_id is not None:
        game = manager.get_game(request.game_id)
        if game is None:
            raise HTTPException(status_code=404, detail=f"Game {request.game_id} not found")
    else:
        game, _ = manager.get_or_create_current()
    try:
        moves = ChessService.legal_targets(game.current_fen, request.square)
    except IllegalMoveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PossibleMovesResponse(square=request.square.lower(), moves=moves)


# ------------------------------------------------------------ two players


def _seat_of(game: Game, token: Optional[str]) -> Optional[str]:
    """Which seat a token belongs to in an online game."""
    if not token:
        return None
    if token == game.white_token:
        return "white"
    if token == game.black_token:
        return "black"
    return None


def _expire_stale_invite(game: Game, manager: GameManager) -> None:
    """Security: unclaimed online invites die after INVITE_TTL_HOURS."""
    if game.mode != "online" or game.is_completed:
        return
    if game.white_name is not None and game.black_name is not None:
        return  # both seats claimed — a running game never expires
    created = game.created_at
    if created.tzinfo is None:  # SQLite returns naive UTC timestamps
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(hours=settings.invite_ttl_hours):
        manager.finish_game(game, result="*", reason="invite_expired")


def _pvp_game_or_404(manager: GameManager, game_id: int) -> Game:
    game = manager.get_game(game_id)
    if game is None or game.mode not in ("local", "online"):
        raise HTTPException(status_code=404, detail=f"Two-player game {game_id} not found")
    _expire_stale_invite(game, manager)
    return game


def _pvp_state(game: Game, manager: GameManager, token: Optional[str] = None) -> PvpStateResponse:
    status = ChessService.status(game.current_fen)
    last = manager.last_move(game.id)
    return PvpStateResponse(
        game_id=game.id,
        mode=game.mode,
        fen=game.current_fen,
        turn=status["turn"],
        pgn=game.pgn,
        in_check=status["in_check"],
        is_game_over=game.is_completed or status["is_game_over"],
        result=game.result if game.is_completed else status["result"],
        move_count=manager.move_count(game.id),
        white_name=game.white_name,
        black_name=game.black_name,
        your_color=_seat_of(game, token),
        opponent_joined=game.mode == "local"
        or (game.white_name is not None and game.black_name is not None),
        last_move=LastMove(
            from_square=last.from_square, to_square=last.to_square, san=last.move_san
        )
        if last
        else None,
    )


@app.post("/api/pvp/games", response_model=PvpCreateResponse)
def create_pvp_game(
    request: PvpCreateRequest,
    manager: GameManager = Depends(get_game_manager),
):
    """Start a two-player game: 'local' (one screen) or 'online' (share link)."""
    if request.mode == "local":
        game = manager.create_pvp_game(
            "local",
            white_name=request.white_name or "White",
            black_name=request.black_name or "Black",
        )
        return PvpCreateResponse(game_id=game.id, mode="local")

    # online: the creator takes a seat, the other seat's token goes in the link
    color = request.creator_color
    if color == "random":
        color = random.choice(["white", "black"])
    white_token = secrets.token_urlsafe(16)
    black_token = secrets.token_urlsafe(16)
    creator_name = request.creator_name or "Player 1"
    game = manager.create_pvp_game(
        "online",
        white_name=creator_name if color == "white" else None,
        black_name=creator_name if color == "black" else None,
        white_token=white_token,
        black_token=black_token,
    )
    return PvpCreateResponse(
        game_id=game.id,
        mode="online",
        your_color=color,
        token=white_token if color == "white" else black_token,
        join_token=black_token if color == "white" else white_token,
    )


@app.post("/api/pvp/games/{game_id}/join", response_model=PvpJoinResponse)
def join_pvp_game(
    game_id: int,
    request: PvpJoinRequest,
    manager: GameManager = Depends(get_game_manager),
):
    """Claim the free seat of an online game using the invite link's token.

    Security: the invite token is single-use — a fresh seat token is minted
    and returned, and the invite token stops working from this point on.
    """
    game = _pvp_game_or_404(manager, game_id)
    if game.mode != "online":
        raise HTTPException(status_code=409, detail="This game is played on one screen.")
    if game.is_completed:
        raise HTTPException(
            status_code=410, detail="This invite has expired or the game is over."
        )
    seat = _seat_of(game, request.token)
    if seat is None:
        raise HTTPException(status_code=403, detail="Invalid invite token.")
    already_named = game.white_name if seat == "white" else game.black_name
    if already_named is not None:
        raise HTTPException(status_code=409, detail="This seat is already taken.")
    fresh_token = secrets.token_urlsafe(16)  # rotate: the invite link dies here
    manager.claim_seat(game, seat, request.name.strip(), new_token=fresh_token)
    return PvpJoinResponse(game_id=game.id, your_color=seat, token=fresh_token)


@app.get("/api/pvp/games/{game_id}/state", response_model=PvpStateResponse)
def pvp_state(
    game_id: int,
    manager: GameManager = Depends(get_game_manager),
    # Security: the seat token travels in a header, never in the URL, so it
    # stays out of browser history, access logs and Referer headers.
    token: Optional[str] = Header(default=None, alias="X-Player-Token"),
):
    game = _pvp_game_or_404(manager, game_id)
    return _pvp_state(game, manager, token)


@app.post("/api/pvp/games/{game_id}/move", response_model=PvpStateResponse)
def pvp_move(
    game_id: int,
    request: PvpMoveRequest,
    manager: GameManager = Depends(get_game_manager),
    token: Optional[str] = Header(default=None, alias="X-Player-Token"),
):
    game = _pvp_game_or_404(manager, game_id)
    if game.is_completed:
        raise HTTPException(status_code=409, detail="Game is already over.")

    status = ChessService.status(game.current_fen)
    if status["is_game_over"]:
        raise HTTPException(status_code=409, detail="Game is already over.")

    if game.mode == "online":
        if game.white_name is None or game.black_name is None:
            raise HTTPException(status_code=409, detail="Waiting for the opponent to join.")
        seat = _seat_of(game, token)
        if seat is None:
            raise HTTPException(status_code=403, detail="Invalid player token.")
        if seat != status["turn"]:
            raise HTTPException(status_code=409, detail="It is not your turn.")

    try:
        outcome = ChessService.apply_move(
            game.current_fen, request.from_square, request.to_square, request.promotion
        )
    except IllegalMoveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mover_name = game.white_name if status["turn"] == "white" else game.black_name
    manager.record_move(
        game,
        from_square=outcome["from_square"],
        to_square=outcome["to_square"],
        san=outcome["san"],
        new_fen=outcome["fen"],
        player=mover_name or status["turn"].capitalize(),
    )
    if outcome["is_game_over"]:
        manager.finish_game(game, result=outcome["result"])
    return _pvp_state(game, manager, token)


@app.post("/api/pvp/games/{game_id}/undo", response_model=PvpStateResponse)
def pvp_undo(
    game_id: int,
    manager: GameManager = Depends(get_game_manager),
):
    """Take back the last half-move. Local (one-screen) games only — online
    undo would need the opponent's consent."""
    game = _pvp_game_or_404(manager, game_id)
    if game.mode != "local":
        raise HTTPException(status_code=409, detail="Undo is only available in local games.")
    if manager.undo_moves(game, plies=1, align_to_user=False) is None:
        raise HTTPException(status_code=409, detail="Nothing to undo.")
    return _pvp_state(game, manager)


# -------------------------------------------------------------------- logs


@app.get("/api/logs/", response_model=List[LogEntryResponse])
def get_logs(
    game_id: Optional[int] = Query(default=None),
    session: Session = Depends(get_session),
    manager: GameManager = Depends(get_game_manager),
):
    """Logs for a specific game, or for the current game when omitted."""
    if game_id is None:
        current = manager.get_current_game()
        if current is None:
            return []
        game_id = current.id
    statement = select(Log).where(Log.game_id == game_id).order_by(Log.id)
    return [
        LogEntryResponse(
            id=log.id,
            game_id=log.game_id,
            timestamp=log.timestamp,
            action_type=log.action_type,
            details=log.details,
        )
        for log in session.exec(statement).all()
    ]


@app.get("/api/health")
def health():
    return {"status": "ok"}
