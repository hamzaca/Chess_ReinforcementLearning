"""LLM-backed chess agent using the Claude API.

The agent builds a context package for each decision — current position
(FEN), full game history (PGN), the exact list of legal moves, and any user
context — and asks Claude to pick a move. The reply is parsed into a
pydantic model via structured outputs, then validated against the legal
move list. Anything unexpected (no API key, network error, refusal,
illegal/parse failure) falls back to the local minimax agent, so the game
never stalls.

Configuration comes from `.env` (see `.env.example`): ANTHROPIC_API_KEY,
LLM_MODEL, AGENT_BACKEND.
"""

from typing import Dict, List, Optional

import chess
from loguru import logger as console
from pydantic import BaseModel, Field

from app.config import settings
from app.agents.chess_agent import ChessAgent

try:  # anthropic is an optional runtime dependency for the minimax-only setup
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


class LlmMoveDecision(BaseModel):
    """Structured output the model must produce (validated by pydantic)."""

    move_san: str = Field(description="The chosen move, exactly as written in the legal moves list")
    reasoning: str = Field(description="One or two sentences explaining the choice")


class LLMChessAgent:
    """Chess agent that delegates move choice to Claude, with minimax fallback."""

    def __init__(self, fallback: Optional[ChessAgent] = None, model: str = ""):
        self.fallback = fallback or ChessAgent()
        self.model = model or settings.llm_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if anthropic is None:
                raise RuntimeError("anthropic package is not installed")
            # api_key=None lets the SDK resolve ANTHROPIC_API_KEY / an
            # `ant auth login` profile from the environment.
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
        return self._client

    # --------------------------------------------------------------- public

    def select_move(
        self,
        fen: str,
        history_sans: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Optional[Dict]:
        board = chess.Board(fen)
        if board.is_game_over(claim_draw=True):
            return None

        legal_sans = [board.san(m) for m in board.legal_moves]
        try:
            decision = self._ask_llm(board, legal_sans, history_sans or [], context or {})
            move = board.parse_san(decision.move_san)  # raises if not legal
            console.info("llm agent chose {} ({})", decision.move_san, decision.reasoning)
            return {
                "from_square": chess.square_name(move.from_square),
                "to_square": chess.square_name(move.to_square),
                "promotion": chess.piece_symbol(move.promotion) if move.promotion else None,
                "uci": move.uci(),
            }
        except Exception as exc:  # noqa: BLE001 — any failure => local fallback
            console.warning("llm agent unavailable ({}); falling back to minimax", exc)
            return self.fallback.select_move(fen, history_sans=history_sans, context=context)

    # ------------------------------------------------------------- internal

    def _ask_llm(
        self,
        board: chess.Board,
        legal_sans: List[str],
        history_sans: List[str],
        context: Dict,
    ) -> LlmMoveDecision:
        color = "White" if board.turn == chess.WHITE else "Black"
        pgn = self._pgn(history_sans) or "(game start — no moves yet)"
        context_lines = "\n".join(f"- {key}: {value}" for key, value in context.items())

        prompt = (
            f"You are playing chess as {color}.\n\n"
            f"Current position (FEN): {board.fen()}\n"
            f"Game so far (PGN): {pgn}\n"
            f"Legal moves (SAN): {', '.join(legal_sans)}\n"
            + (f"Additional context:\n{context_lines}\n" if context_lines else "")
            + "\nChoose the strongest move. `move_san` must be copied verbatim "
            "from the legal moves list above."
        )

        client = self._get_client()
        response = client.messages.parse(
            model=self.model,
            max_tokens=8000,  # hard cap on thinking + answer combined
            output_config={"effort": "low"},  # a single move choice — keep it snappy
            system=(
                "You are a strong chess engine. Consider tactics (captures, "
                "checks, threats), piece safety and development, and the game "
                "history you are given. Always answer with one move taken "
                "verbatim from the provided legal move list."
            ),
            messages=[{"role": "user", "content": prompt}],
            output_format=LlmMoveDecision,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model refused the request")
        decision = response.parsed_output
        if decision is None:
            raise RuntimeError("no parsed output returned")
        return decision

    @staticmethod
    def _pgn(sans: List[str]) -> str:
        parts = []
        for i, san in enumerate(sans):
            parts.append(f"{i // 2 + 1}. {san}" if i % 2 == 0 else san)
        return " ".join(parts)


def get_chess_agent():
    """FastAPI dependency: pick the agent backend from configuration.

    - "minimax": always the local negamax agent.
    - "llm":     always Claude (falls back to minimax on failure).
    - "auto":    Claude when an API key is configured, else minimax.
    """
    minimax = ChessAgent()
    backend = settings.agent_backend.lower()
    if backend == "minimax":
        return minimax
    if backend == "llm" or (backend == "auto" and settings.anthropic_api_key):
        return LLMChessAgent(fallback=minimax)
    return minimax
