"""Game lifecycle management: sessions, DB CRUD, favorites, undo."""

import random
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlmodel import Session, func, select

from app.config import settings
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
        """Most recent unfinished game AGAINST THE AGENT, if any. PvP games
        are addressed by id and never become the implicit current game."""
        statement = (
            select(Game)
            .where(Game.is_completed == False)  # noqa: E712
            .where(Game.mode == "agent")
            .order_by(Game.id.desc())
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

    def _create_game(self, user_color: Optional[str] = None) -> Game:
        # White always moves first (chess rule) — but WHO plays white is
        # random per game unless explicitly requested.
        choice = user_color or settings.default_user_color
        if choice == "random":
            choice = random.choice(["white", "black"])
        game = Game(current_fen=ChessService.starting_fen(), pgn="", user_color=choice)
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.logger.log(
            "game_start",
            game_id=game.id,
            details={"fen": game.current_fen, "user_color": choice},
        )
        return game

    def start_new_game(self, user_color: Optional[str] = None) -> Game:
        """Complete the current game (if any) and create a fresh one."""
        current = self.get_current_game()
        if current is not None:
            self.finish_game(current, result="*", reason="abandoned_for_new_game")
        return self._create_game(user_color=user_color)

    def undo_moves(
        self, game: Game, plies: Optional[int] = None, align_to_user: bool = True
    ) -> Optional[Game]:
        """Take back moves.

        With align_to_user=True (agent games): plies=None takes back the
        user's last move (plus the agent reply after it, if any); an explicit
        ply count rewinds at least that far, always landing on a position
        where the user is to move (or the start of the game).
        With align_to_user=False (PvP games): removes exactly `plies` (or 1)
        half-moves, whoever played them.
        Reopens the game if it was over. Returns None when nothing to undo.
        """
        moves = self.moves_for(game.id)
        total = len(moves)
        if total == 0:
            return None

        def turn_after(ply_count: int) -> str:
            return "white" if ply_count % 2 == 0 else "black"

        target = total - 1 if plies is None else max(0, total - plies)
        if align_to_user:
            while target > 0 and turn_after(target) != game.user_color:
                target -= 1
            # target may be 0 with the agent to move (user plays black) — the
            # caller lets the agent replay its first move in that case.

        for move in moves[target:]:
            self.session.delete(move)

        kept_sans = [m.move_san for m in moves[:target]]
        fens = ChessService.fens_after_sans(kept_sans)
        game.current_fen = fens[-1] if fens else ChessService.starting_fen()
        game.pgn = ChessService.pgn_from_sans(kept_sans)
        game.is_completed = False
        game.result = None
        game.updated_at = utcnow()
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)

        self.logger.log(
            "undo",
            game_id=game.id,
            details={"plies_removed": total - target, "fen": game.current_fen},
        )
        return game

    # ------------------------------------------------------- two players

    def create_pvp_game(
        self,
        mode: str,  # "local" | "online"
        *,
        white_name: Optional[str] = None,
        black_name: Optional[str] = None,
        white_token: Optional[str] = None,
        black_token: Optional[str] = None,
    ) -> Game:
        game = Game(
            current_fen=ChessService.starting_fen(),
            pgn="",
            mode=mode,
            white_name=white_name,
            black_name=black_name,
            white_token=white_token,
            black_token=black_token,
        )
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.logger.log(
            "game_start",
            game_id=game.id,
            details={
                "mode": mode,
                "white_name": white_name,
                "black_name": black_name,
            },
        )
        return game

    def claim_seat(self, game: Game, color: str, name: str, new_token: str) -> Game:
        """Register the joining player on their seat (online games).

        Security: the invite token is single-use — the seat's token is
        ROTATED to `new_token` at claim time, so anyone who saw the invite
        link (forwarded chat, link-preview bot) cannot impersonate the
        player afterwards.
        """
        if color == "white":
            game.white_name = name
            game.white_token = new_token
        else:
            game.black_name = name
            game.black_token = new_token
        game.updated_at = utcnow()
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        self.logger.log(
            "player_join", game_id=game.id, player=name, details={"color": color}
        )
        return game

    def last_move(self, game_id: int) -> Optional[Move]:
        moves = self.moves_for(game_id)
        return moves[-1] if moves else None

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
