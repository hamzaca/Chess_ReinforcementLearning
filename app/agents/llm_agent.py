"""LLM-backed chess agent speaking the OpenAI-compatible chat API.

The agent builds a context package for each decision — current position
(FEN), full game history (PGN), the exact list of legal moves, and memory
(its own rolling plan, recent reasonings and opening-book hints) — and asks
the model to pick a move as a JSON object.

Robustness, in order of defense:
1. Tolerant parsing — code fences and surrounding prose are stripped before
   the JSON is validated; `response_format={"type": "json_object"}` is used
   when the server supports it and silently dropped when it doesn't.
2. Retry with feedback — an illegal move or unparseable reply is fed back to
   the model as a follow-up turn (with the exact error) until
   MAX_LLM_ATTEMPTS total attempts are spent; UCI notation is accepted as a
   fallback for the SAN field.
3. Minimax fallback — anything still failing (server down, timeout, refusal)
   falls back to the local minimax agent, so the game never stalls. The
   returned `engine` field always names the engine that really moved.

Configuration comes from `.env` (see `.env.example`): LLM_BASE_URL (any
OpenAI-compatible endpoint — Anthropic's by default, or a local server),
ANTHROPIC_API_KEY (sent as the bearer token), LLM_MODEL, AGENT_BACKEND,
MAX_LLM_ATTEMPTS, REQUEST_TIMEOUT_S.
"""

import re
from typing import Dict, List, Optional, Tuple

import chess
from loguru import logger as console
from pydantic import BaseModel, Field, ValidationError

from app.agents.chess_agent import ChessAgent
from app.config import Settings, settings

try:  # openai is an optional runtime dependency for the minimax-only setup
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

class LlmMoveDecision(BaseModel):
    """Structured reply the model must produce (validated by pydantic)."""

    move_san: str = Field(description="The chosen move, exactly as written in the legal moves list")
    reasoning: str = Field(description="One or two sentences explaining the choice")
    plan: str = Field(
        default="",
        description="Your strategic plan for the next few moves; it is shown back to you on your next turn",
    )


def _llm_configured() -> bool:
    """True when settings point at a usable LLM backend: an API key, or a
    custom base URL (local servers usually accept any token)."""
    if settings.anthropic_api_key:
        return True
    default_url = Settings.model_fields["llm_base_url"].default
    return bool(settings.llm_base_url) and settings.llm_base_url != default_url


def _extract_json(text: str) -> str:
    """Strip markdown fences / surrounding prose down to the first JSON object."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return text


class LLMChessAgent:
    """Chess agent that delegates move choice to an LLM, with minimax fallback."""

    def __init__(self, fallback: Optional[ChessAgent] = None, model: str = ""):
        """Create the agent.

        Args:
            fallback: agent used when the LLM cannot produce a legal move
                (server down, timeout, persistent bad output). Defaults to a
                fresh minimax ``ChessAgent``.
            model: model tag sent to the server; empty means
                ``settings.llm_model`` (the ``LLM_MODEL`` env var).
        """
        self.fallback = fallback or ChessAgent()
        self.model = model or settings.llm_model
        self._client = None
        # Flipped off after the first server rejection of response_format.
        self._response_format_ok = True

    @property
    def descriptor(self) -> str:
        """Engine identifier used in structured logs."""
        return f"llm:{self.model}"

    def _get_client(self):
        """Lazily build (and cache) the OpenAI-compatible client.

        Configured from settings: ``LLM_BASE_URL`` as the endpoint,
        ``ANTHROPIC_API_KEY`` as the bearer token ("local" when empty — local
        servers usually accept any string), a hard request timeout and a
        single transport-level retry (application retries are handled in
        `_decide_with_retries`).

        Raises:
            RuntimeError: when the ``openai`` package is not installed.
        """
        if self._client is None:
            if OpenAI is None:
                raise RuntimeError("openai package is not installed")
            self._client = OpenAI(
                base_url=settings.llm_base_url or None,
                api_key=settings.anthropic_api_key or "local",
                timeout=settings.request_timeout_s,
                max_retries=1,
            )
        return self._client

    # --------------------------------------------------------------- public

    def select_move(
        self,
        fen: str,
        history_sans: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Pick the agent's move for the given position. Never raises.

        Args:
            fen: current position in FEN notation.
            history_sans: full SAN move history from the start position,
                rendered into the prompt as a PGN.
            context: memory lines for the prompt (rolling plan, recent
                reasonings, opening-book hint) as produced by
                ``AgentMemoryService.get_context``; rendered as "- key: value".

        Returns:
            None when the game is already over; otherwise a move dict with
            ``from_square``/``to_square``/``promotion``/``uci`` plus
            ``engine`` naming the engine that ACTUALLY produced the move
            (``llm:<model>``, or ``minimax(...)`` after a fallback) and — for
            genuine LLM moves — ``reasoning`` and ``plan`` for the memory
            store. Any internal failure degrades to the fallback agent's
            move instead of raising.
        """
        board = chess.Board(fen)
        if board.is_game_over(claim_draw=True):
            return None

        legal_sans = [board.san(m) for m in board.legal_moves]
        try:
            decision, move = self._decide_with_retries(
                board, legal_sans, history_sans or [], context or {}
            )
            san = board.san(move)
            console.info("llm agent chose {} ({})", san, decision.reasoning)
            return {
                "from_square": chess.square_name(move.from_square),
                "to_square": chess.square_name(move.to_square),
                "promotion": chess.piece_symbol(move.promotion) if move.promotion else None,
                "uci": move.uci(),
                "engine": self.descriptor,  # the LLM really answered
                "reasoning": decision.reasoning,
                "plan": decision.plan,
            }
        except Exception as exc:  # noqa: BLE001 — any failure => local fallback
            console.warning("llm agent unavailable ({}); falling back to minimax", exc)
            # The fallback's dict carries engine="minimax(...)" so logs show
            # which engine ACTUALLY produced the move.
            return self.fallback.select_move(fen, history_sans=history_sans, context=context)

    # ------------------------------------------------------------- internal

    def _decide_with_retries(
        self,
        board: chess.Board,
        legal_sans: List[str],
        history_sans: List[str],
        context: Dict,
    ) -> Tuple[LlmMoveDecision, chess.Move]:
        """The retry-with-feedback loop — the robustness core of the agent.

        Runs up to ``MAX_LLM_ATTEMPTS`` (env-configurable, default 3) chat
        completions as ONE growing conversation: when a reply is not the requested JSON object or names
        an illegal move, the rejected reply plus a user turn stating the
        exact error (and the legal move list) are appended, and the model is
        asked again. This turns most one-off hallucinations into a corrected
        second answer instead of a fallback.

        Returns:
            The validated decision and the corresponding legal ``chess.Move``.

        Raises:
            RuntimeError: no attempt produced a legal move (the caller then
                falls back to minimax).
        """
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": self._user_prompt(board, legal_sans, history_sans, context)},
        ]
        attempts = max(1, settings.max_llm_attempts)
        last_error = "no attempts made"
        for attempt in range(1, attempts + 1):
            content = self._complete(messages)
            try:
                decision = LlmMoveDecision.model_validate_json(_extract_json(content))
            except ValidationError as exc:
                last_error = f"reply was not the requested JSON object ({exc.errors()[0]['msg']})"
            else:
                move = self._parse_move(board, decision.move_san)
                if move is not None:
                    return decision, move
                last_error = f"'{decision.move_san}' is not a legal move in this position"
            console.warning("llm attempt {}/{} rejected: {}", attempt, attempts, last_error)
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your answer was rejected: {last_error}.\n"
                        f"Reply again with ONLY a JSON object "
                        f'{{"move_san": ..., "reasoning": ..., "plan": ...}} where move_san is one of: '
                        f"{', '.join(legal_sans)}"
                    ),
                }
            )
        raise RuntimeError(f"no valid move after {attempts} attempts ({last_error})")

    def _complete(self, messages: List[Dict]) -> str:
        """One chat-completion call, returning the raw reply text.

        JSON mode (``response_format={"type": "json_object"}``) is requested
        while the server tolerates it; the first rejection retries the same
        request without it and remembers the downgrade for the rest of this
        agent's lifetime (many local servers do not implement JSON mode —
        `_extract_json` compensates on the parsing side).

        Raises:
            RuntimeError: the server returned an empty completion.
            Exception: transport errors from the client (handled by
                ``select_move``'s fallback).
        """
        client = self._get_client()
        kwargs = {"model": self.model, "max_tokens": 1000, "messages": messages}
        if self._response_format_ok:
            try:
                response = client.chat.completions.create(
                    response_format={"type": "json_object"}, **kwargs
                )
                return self._content_of(response)
            except Exception as exc:  # noqa: BLE001 — server may not support JSON mode
                console.info("server rejected response_format ({}); retrying without", exc)
                self._response_format_ok = False
        response = client.chat.completions.create(**kwargs)
        return self._content_of(response)

    @staticmethod
    def _content_of(response) -> str:
        """Extract the assistant text from a chat-completion response.

        Raises:
            RuntimeError: the response has no choices or empty content
                (treated like any other failed attempt).
        """
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise RuntimeError("empty completion from the LLM server")
        return content

    @staticmethod
    def _parse_move(board: chess.Board, text: str) -> Optional[chess.Move]:
        """Turn the model's ``move_san`` string into a legal move, leniently.

        Tries SAN first (the requested format, e.g. "Nf3", "O-O"), then UCI
        ("g1f3") — models occasionally answer in UCI despite instructions,
        and accepting it saves a retry round-trip.

        Returns:
            The legal ``chess.Move``, or None when the text is neither a
            legal SAN nor a legal UCI move in this position (the caller then
            sends error feedback and retries).
        """
        text = text.strip()
        try:
            return board.parse_san(text)
        except ValueError:
            pass
        try:
            move = board.parse_uci(text.lower())
            return move if move in board.legal_moves else None
        except ValueError:
            return None

    @staticmethod
    def _system_prompt() -> str:
        """System prompt: role (strong engine), what to weigh (tactics,
        safety, history, its own plan) and the strict JSON reply contract
        that `_decide_with_retries` validates against."""
        return (
            "You are a strong chess engine. Consider tactics (captures, checks, "
            "threats), piece safety and development, the game history, and your "
            "own plan from previous turns. Always answer with a single JSON "
            'object {"move_san": ..., "reasoning": ..., "plan": ...} and nothing '
            "else. move_san must be taken verbatim from the provided legal move "
            "list. Keep `plan` to one or two sentences describing your intent "
            "for the next few moves."
        )

    def _user_prompt(
        self,
        board: chess.Board,
        legal_sans: List[str],
        history_sans: List[str],
        context: Dict,
    ) -> str:
        """Build the per-move user prompt: side to move, FEN, PGN so far,
        the exact legal-move list, and — when present — the memory lines
        from ``context`` (rolling plan, recent reasonings, opening-book
        hint) under a "Memory from previous turns" heading. Empty context
        values are skipped so minimax-era games add no noise."""
        color = "White" if board.turn == chess.WHITE else "Black"
        pgn = self._pgn(history_sans) or "(game start — no moves yet)"
        context_lines = "\n".join(f"- {key}: {value}" for key, value in context.items() if value)
        return (
            f"You are playing chess as {color}.\n\n"
            f"Current position (FEN): {board.fen()}\n"
            f"Game so far (PGN): {pgn}\n"
            f"Legal moves (SAN): {', '.join(legal_sans)}\n"
            + (f"Memory from previous turns:\n{context_lines}\n" if context_lines else "")
            + "\nChoose the strongest move and reply with the JSON object only."
        )

    @staticmethod
    def _pgn(sans: List[str]) -> str:
        """Render a SAN list as numbered PGN movetext, e.g.
        ["e4", "e5", "Nf3"] -> "1. e4 e5 2. Nf3". Empty list -> ""."""
        parts = []
        for i, san in enumerate(sans):
            parts.append(f"{i // 2 + 1}. {san}" if i % 2 == 0 else san)
        return " ".join(parts)


def get_chess_agent():
    """FastAPI dependency: pick the agent backend from configuration.

    - "minimax": always the local negamax agent.
    - "llm":     always the LLM (falls back to minimax on failure).
    - "auto":    the LLM when an API key or custom base URL is configured,
                 else minimax.
    """
    minimax = ChessAgent()
    backend = settings.agent_backend.lower()
    if backend == "minimax":
        return minimax
    if backend == "llm" or (backend == "auto" and _llm_configured()):
        return LLMChessAgent(fallback=minimax)
    return minimax
