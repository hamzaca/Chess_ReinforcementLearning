"""Game logger that persists entries to the SQLModel `Log` table.

Injected into endpoints/services via FastAPI dependency injection; it shares
the request-scoped session so log rows commit atomically with the action
they describe. Entries are mirrored to the console via loguru.
"""

from typing import Any, Dict, Optional

from fastapi import Depends
from loguru import logger as console
from sqlmodel import Session

from app.database import get_session
from app.models.sql_models import Log


class GameLogger:
    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        action_type: str,
        *,
        game_id: Optional[int] = None,
        player: Optional[str] = None,  # "User" | "Agent" | None
        details: Optional[Dict[str, Any]] = None,
    ) -> Log:
        """Persist one structured log entry.

        action_type: game_start | resume | move | favorite_toggle | game_over
        """
        payload: Dict[str, Any] = dict(details or {})
        if player is not None:
            payload["player"] = player

        entry = Log(game_id=game_id, action_type=action_type, details=payload)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)

        console.info("game={} action={} details={}", game_id, action_type, payload)
        return entry


def get_game_logger(session: Session = Depends(get_session)) -> GameLogger:
    """FastAPI dependency. Because `get_session` is cached per request, the
    logger shares the same session as the services handling the request."""
    return GameLogger(session)
