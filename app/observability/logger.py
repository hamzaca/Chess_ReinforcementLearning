"""Game logger that persists entries to the SQLModel `Log` table.

Injected into endpoints/services via FastAPI dependency injection; it shares
the request-scoped session so log rows commit atomically with the action
they describe. Entries are mirrored to the console via loguru.

Every persisted entry carries, inside `details`:
- ``status``: "success" | "failed" | "ongoing"
- ``actor``:  who did it — {"type": "user", "name": ...},
              {"type": "player", "name": ..., "color": ...} (PvP),
              {"type": "agent", "model": "minimax(depth=2)" | "llm:claude-..."},
              or {"type": "system"} for lifecycle events.
- ``player``: flat actor name, kept for easy querying/back-compat.

High-frequency read-only endpoints (state polling, possible-moves, listings)
are logged to the console only — persisting them would flood the Log table
(online PvP clients poll every ~2 seconds).
"""

from typing import Any, Dict, Optional

from fastapi import Depends
from loguru import logger as console
from sqlmodel import Session

from app.database import get_session
from app.models.sql_models import Log

# --------------------------------------------------------------- catalog

#: Persisted actions — every state-changing endpoint maps to one of these.
ACTIONS: Dict[str, str] = {
    "game_start": "POST /api/games/new, POST /api/pvp/games, first GET /api/games/current — a game was created",
    "resume": "GET /api/games/current — an unfinished game was resumed",
    "move": "POST /api/move, POST /api/pvp/games/{id}/move — a move attempt (success or failed)",
    "agent_move": "internal — the agent started choosing a move (status=ongoing)",
    "undo": "POST /api/undo, POST /api/pvp/games/{id}/undo — moves taken back (success or failed)",
    "abort": "POST /api/abort, POST /api/pvp/games/{id}/abort — a player aborted the game",
    "game_over": "any endpoint that finishes a game (mate, draw, abort, abandonment, invite expiry)",
    "favorite_toggle": "POST /api/games/{id}/favorite — favorite flag flipped",
    "player_join": "POST /api/pvp/games/{id}/join — a player claimed a seat (success or failed)",
    "invite_expired": "lazy TTL check — an unclaimed online invite expired",
    "unauthorized": "a request with a missing/invalid seat token was rejected",
    "api_call": "EVERY /api/* request — persisted by the access-log middleware "
    "with endpoint, method, HTTP status and duration",
}

#: Console-only actions — read endpoints, too chatty to persist.
READ_ACTIONS: Dict[str, str] = {
    "game_state": "GET /api/game-state, GET /api/pvp/games/{id}/state",
    "possible_moves": "POST /api/possible-moves",
    "replay_view": "GET /api/games/{id}/replay",
    "library_view": "GET /api/games",
    "logs_view": "GET /api/logs/",
}

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_ONGOING = "ongoing"


# ---------------------------------------------------------------- actors


def user_actor(name: Optional[str] = None) -> Dict[str, str]:
    """The human playing against the agent."""
    return {"type": "user", "name": name or "User"}


def player_actor(name: str, color: Optional[str] = None) -> Dict[str, str]:
    """A named human in a two-player game."""
    actor = {"type": "player", "name": name}
    if color:
        actor["color"] = color
    return actor


def agent_actor(model: str) -> Dict[str, str]:
    """The AI agent; `model` identifies the engine that produced the move,
    e.g. "minimax(depth=2)" or "llm:claude-opus-5"."""
    return {"type": "agent", "name": "Agent", "model": model}


def system_actor() -> Dict[str, str]:
    """Lifecycle events not attributable to a person (expiry, bootstrap)."""
    return {"type": "system", "name": "System"}


# ---------------------------------------------------------------- logger


class GameLogger:
    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        action_type: str,
        *,
        game_id: Optional[int] = None,
        status: str = STATUS_SUCCESS,
        actor: Optional[Dict[str, str]] = None,
        player: Optional[str] = None,  # legacy flat name; superseded by actor
        details: Optional[Dict[str, Any]] = None,
    ) -> Log:
        """Persist one structured log entry (see ACTIONS for the catalog)."""
        if action_type not in ACTIONS:
            console.warning("logging unknown action_type {}", action_type)

        payload: Dict[str, Any] = dict(details or {})
        payload["status"] = status
        if actor is not None:
            payload["actor"] = actor
            payload.setdefault("player", actor.get("name"))
        elif player is not None:
            payload["player"] = player

        entry = Log(game_id=game_id, action_type=action_type, details=payload)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)

        console.info(
            "game={} action={} status={} actor={} details={}",
            game_id,
            action_type,
            status,
            (actor or {}).get("name", payload.get("player", "-")),
            {k: v for k, v in payload.items() if k not in ("status", "actor", "player")},
        )
        return entry

    def log_read(self, action_type: str, *, game_id: Optional[int] = None, **info: Any) -> None:
        """Console-only trace for read endpoints (never hits the database)."""
        if action_type not in READ_ACTIONS:
            console.warning("unknown read action_type {}", action_type)
        console.debug("read game={} action={} {}", game_id, action_type, info)


def get_game_logger(session: Session = Depends(get_session)) -> GameLogger:
    """FastAPI dependency. Because `get_session` is cached per request, the
    logger shares the same session as the services handling the request."""
    return GameLogger(session)
