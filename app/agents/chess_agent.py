"""Rule-based chess agent: negamax with alpha-beta pruning.

The agent receives the current position (FEN) plus the game history (SAN
list) and returns a legal move. History matters: the position is rebuilt by
replaying the game so the search can recognize and avoid draw-by-repetition
lines when it is ahead.

# TODO(RL): This is the hook point for the future reinforcement-learning
# model. Replace `_evaluate` with a trained value network and/or replace
# `select_move`'s search with a policy network + MCTS (AlphaZero-style).
# The in-repo `chess_engine` package is the intended dependency-free
# environment for self-play training; the `Move`/`Log` tables provide
# game records for supervised pre-training.
"""

from typing import Dict, List, Optional

import chess

from app.config import settings

_MATE_SCORE = 100_000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Small centralization bonus (piece-square heuristic): pieces score more the
# closer they stand to the four center squares.
_CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]


def _center_bonus(square: int) -> int:
    distance = min(chess.square_distance(square, c) for c in _CENTER)
    return (3 - distance) * 5 if distance < 3 else 0


class ChessAgent:
    """Depth-limited negamax agent. Strength is tuned via `depth` (plies)."""

    def __init__(self, depth: int = settings.agent_depth):
        self.depth = max(1, depth)

    # ------------------------------------------------------------- public

    def select_move(
        self,
        fen: str,
        history_sans: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Pick a legal move for the side to move in `fen`.

        history_sans: full SAN history from the start position; when given,
            the board is rebuilt from it so repetition detection works.
        context: reserved for user context (e.g. difficulty preference).

        Returns {"from_square", "to_square", "promotion", "uci"} or None if
        the game is already over.
        """
        board = self._board_from(fen, history_sans)
        if board.is_game_over(claim_draw=True):
            return None

        best_move: Optional[chess.Move] = None
        best_score = -float("inf")
        alpha, beta = -float("inf"), float("inf")

        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._negamax(board, self.depth - 1, -beta, -alpha)
            # Nudge away from immediate repetitions when not losing.
            if board.is_repetition(2) and score > -200:
                score -= 60
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)

        assert best_move is not None  # legal moves existed
        return {
            "from_square": chess.square_name(best_move.from_square),
            "to_square": chess.square_name(best_move.to_square),
            "promotion": chess.piece_symbol(best_move.promotion) if best_move.promotion else None,
            "uci": best_move.uci(),
        }

    # ------------------------------------------------------------- search

    def _board_from(self, fen: str, history_sans: Optional[List[str]]) -> chess.Board:
        if history_sans:
            board = chess.Board()
            try:
                for san in history_sans:
                    board.push_san(san)
                if board.fen() == fen:
                    return board
            except ValueError:
                pass  # corrupt history — fall back to the FEN alone
        return chess.Board(fen)

    def _ordered_moves(self, board: chess.Board) -> List[chess.Move]:
        """Captures and promotions first — improves alpha-beta pruning."""

        def priority(move: chess.Move) -> int:
            score = 0
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                score += 10 + (PIECE_VALUES[victim.piece_type] // 100 if victim else 1)
            if move.promotion:
                score += 9
            return -score

        return sorted(board.legal_moves, key=priority)

    def _negamax(self, board: chess.Board, depth: int, alpha: float, beta: float) -> float:
        if board.is_checkmate():
            # Side to move is mated; prefer faster mates.
            return -_MATE_SCORE - depth
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0
        if depth <= 0:
            return self._evaluate(board)

        best = -float("inf")
        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            best = max(best, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break  # beta cutoff
        return best

    # --------------------------------------------------------- evaluation

    def _evaluate(self, board: chess.Board) -> float:
        """Static evaluation from the perspective of the side to move.

        # TODO(RL): swap this hand-crafted heuristic for a learned value
        # function once the RL training pipeline exists.
        """
        score = 0
        for square, piece in board.piece_map().items():
            value = PIECE_VALUES[piece.piece_type]
            if piece.piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP):
                value += _center_bonus(square)
            score += value if piece.color == chess.WHITE else -value
        return score if board.turn == chess.WHITE else -score


def get_chess_agent() -> ChessAgent:
    """FastAPI dependency."""
    return ChessAgent()
