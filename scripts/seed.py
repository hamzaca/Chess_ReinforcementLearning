"""Seed the database with a sample completed game (Scholar's mate).

Run from the repository root: python scripts/seed.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.observability.logger import GameLogger  # noqa: E402
from app.services.chess_service import ChessService  # noqa: E402
from app.services.game_manager import GameManager  # noqa: E402

SCHOLARS_MATE = [
    ("e2", "e4"), ("e7", "e5"),
    ("f1", "c4"), ("b8", "c6"),
    ("d1", "h5"), ("g8", "f6"),
    ("h5", "f7"),  # Qxf7#
]


def main() -> None:
    init_db()
    with Session(engine) as session:
        manager = GameManager(session, GameLogger(session))
        game = manager.start_new_game(user_color="white")
        fen = game.current_fen
        for i, (from_sq, to_sq) in enumerate(SCHOLARS_MATE):
            outcome = ChessService.apply_move(fen, from_sq, to_sq)
            manager.record_move(
                game,
                from_square=from_sq,
                to_square=to_sq,
                san=outcome["san"],
                new_fen=outcome["fen"],
                player="User" if i % 2 == 0 else "Agent",
            )
            fen = outcome["fen"]
        manager.finish_game(game, result="1-0")
        manager.toggle_favorite(game.id)
        print(f"Seeded game #{game.id}: Scholar's mate ({game.pgn})")


if __name__ == "__main__":
    main()
