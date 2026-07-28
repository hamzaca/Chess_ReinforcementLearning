"""FastAPI entry point for the Chess AI application.

The user always plays White; the agent answers as Black. If the server is
restarted between the user's move and the agent's reply, the agent catches
up automatically the next time the current game is fetched.
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.agents.chess_agent import ChessAgent, get_chess_agent
from app.config import settings
from app.database import get_session, init_db
from app.models.schemas import (
    CurrentGameResponse,
    FavoriteResponse,
    GameStateResponse,
    GameSummary,
    LogEntryResponse,
    MovePlayed,
    MoveRequest,
    MoveResponse,
    PossibleMovesRequest,
    PossibleMovesResponse,
    ReplayResponse,
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


app = FastAPI(title="Chess AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------- helpers


def _agent_reply(game: Game, manager: GameManager, agent: ChessAgent) -> Optional[MovePlayed]:
    """If it is Black's turn in `game`, let the agent move. Returns the move
    played (or None). Finishes the game when the agent's move ends it."""
    status = ChessService.status(game.current_fen)
    if status["is_game_over"] or status["turn"] != "black":
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
        in_check=status["in_check"],
        is_game_over=game.is_completed or status["is_game_over"],
        result=game.result if game.is_completed else status["result"],
        move_count=manager.move_count(game.id),
    )


# ------------------------------------------------------------------- games


@app.get("/api/games/current", response_model=CurrentGameResponse)
def get_current_game(
    manager: GameManager = Depends(get_game_manager),
    agent: ChessAgent = Depends(get_chess_agent),
):
    """Most recent unfinished game; creates one if none exists."""
    game, created = manager.get_or_create_current()
    # Catch up if the server previously stopped before the agent replied.
    _agent_reply(game, manager, agent)
    status = ChessService.status(game.current_fen)
    return CurrentGameResponse(
        game_id=game.id,
        fen=game.current_fen,
        turn=status["turn"],
        pgn=game.pgn,
        created=created,
        in_check=status["in_check"],
        is_game_over=game.is_completed or status["is_game_over"],
        result=game.result if game.is_completed else status["result"],
    )


@app.post("/api/games/new", response_model=CurrentGameResponse)
def new_game(manager: GameManager = Depends(get_game_manager)):
    """Complete the current game and start a fresh one."""
    game = manager.start_new_game()
    status = ChessService.status(game.current_fen)
    return CurrentGameResponse(
        game_id=game.id,
        fen=game.current_fen,
        turn=status["turn"],
        pgn=game.pgn,
        created=True,
        in_check=status["in_check"],
        is_game_over=False,
        result=None,
    )


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
    agent: ChessAgent = Depends(get_chess_agent),
):
    game, _ = manager.get_or_create_current()
    if game.is_completed:
        raise HTTPException(status_code=409, detail="Game is already over. Start a new game.")

    status = ChessService.status(game.current_fen)
    if status["is_game_over"]:
        raise HTTPException(status_code=409, detail="Game is already over. Start a new game.")
    if status["turn"] != "white":
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
        in_check=final_status["in_check"],
        is_game_over=game.is_completed or final_status["is_game_over"],
        result=game.result if game.is_completed else final_status["result"],
    )


@app.post("/api/possible-moves", response_model=PossibleMovesResponse)
def possible_moves(
    request: PossibleMovesRequest,
    manager: GameManager = Depends(get_game_manager),
):
    game, _ = manager.get_or_create_current()
    try:
        moves = ChessService.legal_targets(game.current_fen, request.square)
    except IllegalMoveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PossibleMovesResponse(square=request.square.lower(), moves=moves)


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
