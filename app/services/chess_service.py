"""Stateless chess-rules service.

Uses python-chess as the authoritative validator/notation engine (per the
architecture decision: battle-tested SAN/PGN/draw rules), while the in-repo
``chess_engine`` package remains the dependency-free board representation
for the future RL environment. The two are cross-validated in tests.
"""

from typing import Dict, List, Optional

import chess

STARTING_FEN = chess.STARTING_FEN


class IllegalMoveError(ValueError):
    """The requested move is not legal in the current position."""


class ChessService:
    """Pure functions over FEN strings — all game state lives in the DB."""

    @staticmethod
    def starting_fen() -> str:
        return STARTING_FEN

    @staticmethod
    def turn(fen: str) -> str:
        return "white" if chess.Board(fen).turn == chess.WHITE else "black"

    @staticmethod
    def status(fen: str) -> Dict:
        board = chess.Board(fen)
        is_over = board.is_game_over(claim_draw=True)
        return {
            "turn": "white" if board.turn == chess.WHITE else "black",
            "in_check": board.is_check(),
            "is_game_over": is_over,
            "result": board.result(claim_draw=True) if is_over else None,
        }

    @staticmethod
    def legal_targets(fen: str, from_square: str) -> List[str]:
        """All destination squares reachable from `from_square`."""
        board = chess.Board(fen)
        try:
            square = chess.parse_square(from_square.lower())
        except ValueError as exc:
            raise IllegalMoveError(f"invalid square {from_square!r}") from exc
        return sorted(
            {chess.square_name(m.to_square) for m in board.legal_moves if m.from_square == square}
        )

    @staticmethod
    def apply_move(
        fen: str,
        from_square: str,
        to_square: str,
        promotion: Optional[str] = None,
    ) -> Dict:
        """Validate and apply a move. Returns the new FEN, the SAN of the
        move played, and the resulting game status.

        Raises IllegalMoveError on anything that is not a legal move.
        """
        board = chess.Board(fen)
        try:
            from_sq = chess.parse_square(from_square.lower())
            to_sq = chess.parse_square(to_square.lower())
        except ValueError as exc:
            raise IllegalMoveError(f"invalid square in {from_square!r}->{to_square!r}") from exc

        promo_piece = None
        piece = board.piece_at(from_sq)
        if piece is not None and piece.piece_type == chess.PAWN and chess.square_rank(to_sq) in (0, 7):
            # Default to queen when the client does not specify a promotion.
            promo_piece = chess.Piece.from_symbol(promotion or "q").piece_type

        move = chess.Move(from_sq, to_sq, promotion=promo_piece)
        if move not in board.legal_moves:
            raise IllegalMoveError(f"illegal move {from_square}->{to_square}")

        san = board.san(move)
        board.push(move)
        is_over = board.is_game_over(claim_draw=True)
        return {
            "fen": board.fen(),
            "san": san,
            "from_square": chess.square_name(from_sq),
            "to_square": chess.square_name(to_sq),
            "turn": "white" if board.turn == chess.WHITE else "black",
            "in_check": board.is_check(),
            "is_game_over": is_over,
            "result": board.result(claim_draw=True) if is_over else None,
        }

    @staticmethod
    def pgn_from_sans(sans: List[str]) -> str:
        """Build a movetext PGN string ("1. e4 e5 2. Nf3 ...") from SANs."""
        parts: List[str] = []
        for i, san in enumerate(sans):
            if i % 2 == 0:
                parts.append(f"{i // 2 + 1}. {san}")
            else:
                parts.append(san)
        return " ".join(parts)

    @staticmethod
    def fens_after_sans(sans: List[str]) -> List[str]:
        """Replay a SAN list from the start position; FEN after each ply."""
        board = chess.Board()
        fens: List[str] = []
        for san in sans:
            board.push_san(san)
            fens.append(board.fen())
        return fens
