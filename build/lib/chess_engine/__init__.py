"""chess_engine — a clean, UI-free chess library.

This package is the refactor of the original ``chess/`` pygame code
(now archived in ``legacy_pygame_chess/``). It fixes every known bug of
the legacy engine:

1.  ``get_color`` property/method mismatch  -> plain attributes (`piece.color`).
2.  ``Game.py`` NameError on ``EmptyCell``  -> no EmptyCell class at all;
    empty squares are simply ``None`` and the module has no cross-import cycles.
3.  Color/pawn-direction bug               -> pawn direction is derived from the
    piece color, never from "player 1 / player 2" seating.
4.  Stale coordinates after capture        -> pieces are immutable and do NOT
    store coordinates; position lives only in the Board, so it can never go stale.
5.  Unsound checkmate simulation           -> move legality is checked on a real
    board copy via ``Board.copy()`` + attack scans; no shared mutable pieces.
6.  Missing rules                          -> castling, en passant, promotion and
    "cannot move into check / pinned pieces" are fully implemented and
    cross-validated against python-chess with perft tests (see tests/).

The production API service uses python-chess for SAN/PGN notation; this module
is the dependency-free board representation intended as the future RL
environment (state encoding, self-play, etc.).
"""

from chess_engine.board import (
    BLACK,
    START_FEN,
    WHITE,
    Board,
    IllegalMoveError,
    Move,
    Piece,
    other,
    parse_square,
    square_name,
)

__all__ = [
    "BLACK",
    "START_FEN",
    "WHITE",
    "Board",
    "IllegalMoveError",
    "Move",
    "Piece",
    "other",
    "parse_square",
    "square_name",
]
