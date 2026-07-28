"""Core board, piece and move-generation logic.

Conventions
-----------
* A square is a ``(file, rank)`` tuple, both 0-7. ``(0, 0)`` is a1 (white's
  queenside corner), ``(7, 7)`` is h8. ``square_name((4, 0)) == "e1"``.
* White pawns always move towards rank 7, black pawns towards rank 0 —
  direction is a function of *color*, not of which "player" owns the piece.
* Pieces are immutable value objects without coordinates; the Board is the
  single source of truth for where everything stands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

WHITE = "white"
BLACK = "black"

FILES = "abcdefgh"
PROMOTABLE = ("Q", "R", "B", "N")

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

Square = Tuple[int, int]

KNIGHT_OFFSETS = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
KING_OFFSETS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

# Squares whose involvement in a move (as origin or destination) revokes
# castling rights.
_CASTLING_MASK = {
    (4, 0): "KQ",  # white king home
    (0, 0): "Q",   # white queenside rook home
    (7, 0): "K",   # white kingside rook home
    (4, 7): "kq",  # black king home
    (0, 7): "q",
    (7, 7): "k",
}


class IllegalMoveError(ValueError):
    """Raised when a move that is not legal in the current position is pushed."""


def other(color: str) -> str:
    return BLACK if color == WHITE else WHITE


def square_name(sq: Square) -> str:
    f, r = sq
    return f"{FILES[f]}{r + 1}"


def parse_square(name: str) -> Square:
    name = name.strip().lower()
    if len(name) != 2 or name[0] not in FILES or not name[1].isdigit():
        raise ValueError(f"invalid square name: {name!r}")
    rank = int(name[1]) - 1
    if not 0 <= rank <= 7:
        raise ValueError(f"invalid square name: {name!r}")
    return (FILES.index(name[0]), rank)


@dataclass(frozen=True)
class Piece:
    """An immutable chess piece. It intentionally has no coordinates."""

    color: str  # WHITE or BLACK
    kind: str   # one of "PNBRQK"

    @property
    def fen_char(self) -> str:
        return self.kind if self.color == WHITE else self.kind.lower()

    @classmethod
    def from_fen_char(cls, ch: str) -> "Piece":
        return cls(WHITE if ch.isupper() else BLACK, ch.upper())

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Piece({self.color} {self.kind})"


@dataclass(frozen=True)
class Move:
    from_sq: Square
    to_sq: Square
    promotion: Optional[str] = None  # "Q", "R", "B" or "N"

    @property
    def uci(self) -> str:
        suffix = self.promotion.lower() if self.promotion else ""
        return f"{square_name(self.from_sq)}{square_name(self.to_sq)}{suffix}"

    @classmethod
    def from_uci(cls, uci: str) -> "Move":
        uci = uci.strip().lower()
        if len(uci) not in (4, 5):
            raise ValueError(f"invalid UCI move: {uci!r}")
        promotion = uci[4].upper() if len(uci) == 5 else None
        if promotion is not None and promotion not in PROMOTABLE:
            raise ValueError(f"invalid promotion piece: {uci!r}")
        return cls(parse_square(uci[0:2]), parse_square(uci[2:4]), promotion)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Move({self.uci})"


class Board:
    """Full chess position: piece placement, side to move, castling rights,
    en-passant target and move clocks. Supports full legal move generation."""

    def __init__(self, fen: str = START_FEN):
        # squares[rank][file] -> Piece | None
        self.squares: List[List[Optional[Piece]]] = [[None] * 8 for _ in range(8)]
        self.turn: str = WHITE
        self.castling: set = set()          # subset of {"K","Q","k","q"}
        self.ep_target: Optional[Square] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self._load_fen(fen)

    # ------------------------------------------------------------------ FEN

    def _load_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) < 4:
            raise ValueError(f"invalid FEN: {fen!r}")
        placement, turn, castling, ep = parts[0], parts[1], parts[2], parts[3]
        halfmove = parts[4] if len(parts) > 4 else "0"
        fullmove = parts[5] if len(parts) > 5 else "1"

        rows = placement.split("/")
        if len(rows) != 8:
            raise ValueError(f"invalid FEN placement: {placement!r}")
        for fen_rank, row in enumerate(rows):
            rank = 7 - fen_rank  # first FEN row is rank 8
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                else:
                    if file > 7 or ch.upper() not in "PNBRQK":
                        raise ValueError(f"invalid FEN placement: {placement!r}")
                    self.squares[rank][file] = Piece.from_fen_char(ch)
                    file += 1
            if file != 8:
                raise ValueError(f"invalid FEN placement row: {row!r}")

        self.turn = WHITE if turn == "w" else BLACK
        self.castling = set(castling) if castling != "-" else set()
        self.ep_target = parse_square(ep) if ep != "-" else None
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)

    def fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file in range(8):
                piece = self.squares[rank][file]
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece.fen_char
            if empty:
                row += str(empty)
            rows.append(row)
        castling = "".join(c for c in "KQkq" if c in self.castling) or "-"
        ep = square_name(self.ep_target) if self.ep_target else "-"
        return " ".join(
            [
                "/".join(rows),
                "w" if self.turn == WHITE else "b",
                castling,
                ep,
                str(self.halfmove_clock),
                str(self.fullmove_number),
            ]
        )

    # ------------------------------------------------------------- basics

    def piece_at(self, sq: Square) -> Optional[Piece]:
        f, r = sq
        return self.squares[r][f]

    def king_square(self, color: str) -> Optional[Square]:
        target = Piece(color, "K")
        for r in range(8):
            for f in range(8):
                if self.squares[r][f] == target:
                    return (f, r)
        return None

    def copy(self) -> "Board":
        clone = Board.__new__(Board)
        clone.squares = [row[:] for row in self.squares]
        clone.turn = self.turn
        clone.castling = set(self.castling)
        clone.ep_target = self.ep_target
        clone.halfmove_clock = self.halfmove_clock
        clone.fullmove_number = self.fullmove_number
        return clone

    # ------------------------------------------------------- attack scans

    def is_attacked(self, sq: Square, by: str) -> bool:
        """True if `sq` is attacked by any piece of color `by`."""
        f, r = sq

        # Pawn attacks: a `by`-colored pawn one rank *behind* sq (from the
        # attacker's perspective) on an adjacent file attacks sq.
        direction = 1 if by == WHITE else -1
        for df in (-1, 1):
            af, ar = f + df, r - direction
            if 0 <= af <= 7 and 0 <= ar <= 7:
                piece = self.squares[ar][af]
                if piece is not None and piece.color == by and piece.kind == "P":
                    return True

        # Knight attacks.
        for df, dr in KNIGHT_OFFSETS:
            af, ar = f + df, r + dr
            if 0 <= af <= 7 and 0 <= ar <= 7:
                piece = self.squares[ar][af]
                if piece is not None and piece.color == by and piece.kind == "N":
                    return True

        # King adjacency.
        for df, dr in KING_OFFSETS:
            af, ar = f + df, r + dr
            if 0 <= af <= 7 and 0 <= ar <= 7:
                piece = self.squares[ar][af]
                if piece is not None and piece.color == by and piece.kind == "K":
                    return True

        # Sliding attacks.
        for dirs, kinds in ((ROOK_DIRS, ("R", "Q")), (BISHOP_DIRS, ("B", "Q"))):
            for df, dr in dirs:
                af, ar = f + df, r + dr
                while 0 <= af <= 7 and 0 <= ar <= 7:
                    piece = self.squares[ar][af]
                    if piece is not None:
                        if piece.color == by and piece.kind in kinds:
                            return True
                        break
                    af += df
                    ar += dr
        return False

    def is_check(self, color: Optional[str] = None) -> bool:
        color = color or self.turn
        king = self.king_square(color)
        if king is None:
            return False
        return self.is_attacked(king, other(color))

    # ---------------------------------------------------- move generation

    def _pseudo_legal_moves(self) -> Iterator[Move]:
        color = self.turn
        for r in range(8):
            for f in range(8):
                piece = self.squares[r][f]
                if piece is None or piece.color != color:
                    continue
                yield from self._piece_moves((f, r), piece)

    def _piece_moves(self, sq: Square, piece: Piece) -> Iterator[Move]:
        f, r = sq
        color = piece.color

        if piece.kind == "P":
            direction = 1 if color == WHITE else -1
            start_rank = 1 if color == WHITE else 6
            promo_rank = 7 if color == WHITE else 0

            def pawn_moves(to_sq: Square) -> Iterator[Move]:
                if to_sq[1] == promo_rank:
                    for promo in PROMOTABLE:
                        yield Move(sq, to_sq, promo)
                else:
                    yield Move(sq, to_sq)

            # Single push.
            one = (f, r + direction)
            if 0 <= one[1] <= 7 and self.piece_at(one) is None:
                yield from pawn_moves(one)
                # Double push from the start rank (rank check, not a mutable
                # "is_first_move" flag — this fixes the legacy engine bug).
                if r == start_rank:
                    two = (f, r + 2 * direction)
                    if self.piece_at(two) is None:
                        yield Move(sq, two)
            # Captures (including en passant).
            for df in (-1, 1):
                to_sq = (f + df, r + direction)
                if not (0 <= to_sq[0] <= 7 and 0 <= to_sq[1] <= 7):
                    continue
                target = self.piece_at(to_sq)
                if target is not None and target.color != color:
                    yield from pawn_moves(to_sq)
                elif target is None and to_sq == self.ep_target:
                    yield Move(sq, to_sq)
            return

        if piece.kind == "N" or piece.kind == "K":
            offsets = KNIGHT_OFFSETS if piece.kind == "N" else KING_OFFSETS
            for df, dr in offsets:
                to_f, to_r = f + df, r + dr
                if 0 <= to_f <= 7 and 0 <= to_r <= 7:
                    target = self.squares[to_r][to_f]
                    if target is None or target.color != color:
                        yield Move(sq, (to_f, to_r))
            if piece.kind == "K":
                yield from self._castling_moves(color)
            return

        # Sliding pieces.
        dirs = {"R": ROOK_DIRS, "B": BISHOP_DIRS, "Q": ROOK_DIRS + BISHOP_DIRS}[piece.kind]
        for df, dr in dirs:
            to_f, to_r = f + df, r + dr
            while 0 <= to_f <= 7 and 0 <= to_r <= 7:
                target = self.squares[to_r][to_f]
                if target is None:
                    yield Move(sq, (to_f, to_r))
                else:
                    if target.color != color:
                        yield Move(sq, (to_f, to_r))
                    break
                to_f += df
                to_r += dr

    def _castling_moves(self, color: str) -> Iterator[Move]:
        rank = 0 if color == WHITE else 7
        king_sq = (4, rank)
        if self.piece_at(king_sq) != Piece(color, "K"):
            return
        enemy = other(color)
        kingside_right = "K" if color == WHITE else "k"
        queenside_right = "Q" if color == WHITE else "q"

        if kingside_right in self.castling and self.piece_at((7, rank)) == Piece(color, "R"):
            if (
                self.piece_at((5, rank)) is None
                and self.piece_at((6, rank)) is None
                and not self.is_attacked((4, rank), enemy)
                and not self.is_attacked((5, rank), enemy)
                and not self.is_attacked((6, rank), enemy)
            ):
                yield Move(king_sq, (6, rank))

        if queenside_right in self.castling and self.piece_at((0, rank)) == Piece(color, "R"):
            if (
                self.piece_at((1, rank)) is None
                and self.piece_at((2, rank)) is None
                and self.piece_at((3, rank)) is None
                and not self.is_attacked((4, rank), enemy)
                and not self.is_attacked((3, rank), enemy)
                and not self.is_attacked((2, rank), enemy)
            ):
                yield Move(king_sq, (2, rank))

    def legal_moves(self) -> List[Move]:
        """All strictly legal moves: pseudo-legal moves that do not leave the
        mover's own king in check (this covers pins and moving into check —
        rules the legacy engine did not enforce)."""
        color = self.turn
        moves = []
        for move in self._pseudo_legal_moves():
            probe = self.copy()
            probe._apply(move)
            if not probe.is_check(color):
                moves.append(move)
        return moves

    def legal_moves_from(self, sq: Square) -> List[Move]:
        return [m for m in self.legal_moves() if m.from_sq == sq]

    def is_legal(self, move: Move) -> bool:
        return move in self.legal_moves()

    # ------------------------------------------------------- making moves

    def _apply(self, move: Move) -> None:
        """Apply a pseudo-legal move without legality validation."""
        from_f, from_r = move.from_sq
        to_f, to_r = move.to_sq
        piece = self.squares[from_r][from_f]
        if piece is None:
            raise IllegalMoveError(f"no piece on {square_name(move.from_sq)}")
        captured = self.squares[to_r][to_f]
        new_ep_target: Optional[Square] = None

        if piece.kind == "P":
            # En passant capture: pawn moves diagonally onto an empty square.
            if captured is None and from_f != to_f and move.to_sq == self.ep_target:
                self.squares[from_r][to_f] = None  # remove the passed pawn
                captured = Piece(other(piece.color), "P")
            # Double push sets the en-passant target.
            if abs(to_r - from_r) == 2:
                new_ep_target = (from_f, (from_r + to_r) // 2)

        if piece.kind == "K" and abs(to_f - from_f) == 2:
            # Castling: also move the rook.
            rank = from_r
            if to_f == 6:  # kingside
                self.squares[rank][5] = self.squares[rank][7]
                self.squares[rank][7] = None
            else:  # queenside
                self.squares[rank][3] = self.squares[rank][0]
                self.squares[rank][0] = None

        # Update castling rights based on origin/destination squares.
        for sq in (move.from_sq, move.to_sq):
            for right in _CASTLING_MASK.get(sq, ""):
                self.castling.discard(right)

        # Move (and possibly promote) the piece. The piece object itself is
        # immutable — its position is defined only by where the board puts it,
        # so captures can never leave stale coordinates behind.
        if move.promotion:
            piece = Piece(piece.color, move.promotion)
        self.squares[to_r][to_f] = piece
        self.squares[from_r][from_f] = None

        self.ep_target = new_ep_target
        if piece.kind == "P" or move.promotion or captured is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if self.turn == BLACK:
            self.fullmove_number += 1
        self.turn = other(self.turn)

    def push(self, move: Move) -> None:
        """Validate and apply a move; raises IllegalMoveError if not legal."""
        if not self.is_legal(move):
            raise IllegalMoveError(f"illegal move {move.uci} in position {self.fen()}")
        self._apply(move)

    def push_uci(self, uci: str) -> Move:
        move = Move.from_uci(uci)
        # Auto-promote to queen if the caller omitted the promotion piece.
        piece = self.piece_at(move.from_sq)
        if (
            move.promotion is None
            and piece is not None
            and piece.kind == "P"
            and move.to_sq[1] in (0, 7)
        ):
            move = Move(move.from_sq, move.to_sq, "Q")
        self.push(move)
        return move

    # ----------------------------------------------------------- verdicts

    def is_checkmate(self) -> bool:
        return self.is_check() and not self.legal_moves()

    def is_stalemate(self) -> bool:
        return not self.is_check() and not self.legal_moves()

    def is_game_over(self) -> bool:
        # NOTE: 50-move/threefold-repetition draws are handled at the service
        # layer (python-chess); here game-over means mate or stalemate.
        return not self.legal_moves()

    def result(self) -> Optional[str]:
        if self.is_checkmate():
            return "0-1" if self.turn == WHITE else "1-0"
        if self.is_stalemate():
            return "1/2-1/2"
        return None

    # -------------------------------------------------------------- utils

    def perft(self, depth: int) -> int:
        """Count leaf nodes of the legal move tree (used by the test suite to
        cross-validate this engine against python-chess)."""
        if depth <= 0:
            return 1
        total = 0
        for move in self.legal_moves():
            probe = self.copy()
            probe._apply(move)
            total += probe.perft(depth - 1)
        return total

    def __str__(self) -> str:  # pragma: no cover - debug aid
        lines = []
        for rank in range(7, -1, -1):
            cells = [
                (self.squares[rank][f].fen_char if self.squares[rank][f] else ".")
                for f in range(8)
            ]
            lines.append(f"{rank + 1} " + " ".join(cells))
        lines.append("  a b c d e f g h")
        return "\n".join(lines)
