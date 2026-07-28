"""Replay service: stored move history plus per-ply FEN reconstruction."""

from typing import Optional

from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.models.schemas import ReplayMove, ReplayResponse
from app.services.chess_service import ChessService
from app.services.game_manager import GameManager, get_game_manager


class ReplayService:
    def __init__(self, session: Session, manager: GameManager):
        self.session = session
        self.manager = manager

    def get_replay(self, game_id: int) -> Optional[ReplayResponse]:
        game = self.manager.get_game(game_id)
        if game is None:
            return None
        moves = self.manager.moves_for(game_id)
        # Reconstruct the position after each ply so the frontend can step
        # through the game without needing a chess engine of its own.
        fens = ChessService.fens_after_sans([m.move_san for m in moves])
        return ReplayResponse(
            game_id=game_id,
            pgn=game.pgn,
            start_fen=ChessService.starting_fen(),
            moves=[
                ReplayMove(
                    move_number=m.move_number,
                    from_square=m.from_square,
                    to_square=m.to_square,
                    move_san=m.move_san,
                    fen_after=fen,
                )
                for m, fen in zip(moves, fens)
            ],
        )


def get_replay_service(
    session: Session = Depends(get_session),
    manager: GameManager = Depends(get_game_manager),
) -> ReplayService:
    return ReplayService(session, manager)
