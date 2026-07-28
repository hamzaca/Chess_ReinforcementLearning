"""Game lifecycle management: sessions, DB CRUD, favorites."""

from typing import List, Optional, Tuple

from fastapi import Depends
from sqlmodel import Session, func, select

from app.database import get_session
from app.models.sql_models import Game, Move, utcnow
from app.observability.logger import GameLogger, get_game_logger
from app.services.chess_service import ChessService


class GameManager:
    def __init__(self, session: Session, logger: GameLogger):
        self.session = session
        self.logger = logger

    # ------------------------------------------------------------ queries

    def get_game(self, game_id: int) -> Optional[Game]:
        return self.session.get(Game, game_id)

    def get_current_game(self) -> Optional[Game]:
        """Most recent game that is not completed, if any."""
        statement = (
            select(Game).where(Game.is_completed == False).order_by(Game.id.desc())  # noqa: E712
        )
        return self.session.exec(statement).first()

    def get_or_create_current(self) -> Tuple[Game, bool]:
        """Return (game, created). Logs `resume` or `game_start`."""
        game = self.get_current_game()
        if game is not None:
            self.logger.log("resume", game_id=game.id, details={"fen": game.current_fen})
            return game, False
        return self._create_game(), True

    def list_games(self, favorites_only: bool = False) -> List[Game]:
        statement = select(Game)
        if favorites_only:
            statement = statement.where(Game.is_favorite == True)  # noqa: E712
        statement = statement.order_by(Game.id.desc())
        return list(self.session.exec(statement).all())

    def move_count(self, game_id: int) -> int:
        statement = select(func.count()).select_from(Move).where(Move.game_id == game_id)
        return int(self.session.exec(statement).one())

    def moves_for(self, game_id: int) -> List[Move]:
        statement = (
            select(Move).where(Move.game_id == game_id).order_by(Move.move_number)
        )
        return list(self.session.exec(statement).all())

    # ----------------------------------------------------------- commands

    def _create_game(self) -> Game:
        game = Game(current_fen=ChessService.starting_fen(), pgn="")
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.logger.log("game_start", game_id=game.id, details={"fen": game.current_fen})
        return game

    def start_new_game(self) -> Game:
        """Complete the current game (if any) and create a fresh one."""
        current = self.get_current_game()
        if current is not None:
            self.finish_game(current, result="*", reason="abandoned_for_new_game")
        return self._create_game()

    def record_move(
        self,
        game: Game,
        *,
        from_square: str,
        to_square: str,
        san: str,
        new_fen: str,
        player: str,  # "User" | "Agent"
    ) -> Move:
        # Collect history BEFORE adding the new move: autoflush would make a
        # later query see the pending row and duplicate its SAN in the PGN.
        sans = [m.move_san for m in self.moves_for(game.id)] + [san]
        move = Move(
            game_id=game.id,
            move_number=len(sans),
            from_square=from_square,
            to_square=to_square,
            move_san=san,
        )
        self.session.add(move)
        game.current_fen = new_fen
        game.pgn = ChessService.pgn_from_sans(sans)
        game.updated_at = utcnow()
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.session.refresh(move)

        self.logger.log(
            "move",
            game_id=game.id,
            player=player,
            details={
                "move_number": move.move_number,
                "from": from_square,
                "to": to_square,
                "san": san,
                "fen": new_fen,
            },
        )
        return move

    def finish_game(self, game: Game, *, result: str, reason: str = "") -> Game:
        game.is_completed = True
        game.result = result
        game.updated_at = utcnow()
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        details = {"result": result}
        if reason:
            details["reason"] = reason
        self.logger.log("game_over", game_id=game.id, details=details)
        return game

    def toggle_favorite(self, game_id: int) -> Optional[Game]:
        game = self.get_game(game_id)
        if game is None:
            return None
        game.is_favorite = not game.is_favorite
        game.updated_at = utcnow()
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.logger.log(
            "favorite_toggle", game_id=game.id, details={"is_favorite": game.is_favorite}
        )
        return game


def get_game_manager(
    session: Session = Depends(get_session),
    logger: GameLogger = Depends(get_game_logger),
) -> GameManager:
    return GameManager(session, logger)
