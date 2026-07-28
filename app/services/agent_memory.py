"""Working memory and opening book for the LLM agent.

Two kinds of memory, both in the regular SQL database (retrieval is exact-key
by game id / position — no need for a vector store):

- **In-game memory** (`agent_memory` table): after every agent move the
  agent's `plan` and `reasoning` are persisted; the next prompt gets the
  latest plan plus the last few reasonings, so the agent plays coherently
  across moves and server restarts. Rows past the current position are
  pruned on undo.
- **Opening book** (`opening_book` table): when an agent game ends decisively
  the agent's early moves are recorded per position (clock-stripped FEN, so
  transpositions collapse) with win/loss counts. Positive lines are offered
  to the LLM as a *hint* in the prompt — never played blindly.
"""

from typing import Dict, List, Optional

import chess
from sqlmodel import Session, select

from app.models.sql_models import AgentMemory, Game, Move, OpeningBookEntry

#: Only the first 20 plies (~10 full moves) feed the opening book.
BOOK_PLY_LIMIT = 20
#: How many past reasonings are shown back to the agent.
RECENT_REASONINGS = 3
#: At most this many book moves are suggested per position.
BOOK_HINTS = 3


def position_key(fen: str) -> str:
    """FEN without the halfmove/fullmove clocks — a transposition-stable
    opening-book key (same position => same key regardless of move order)."""
    return " ".join(fen.split()[:4])


class AgentMemoryService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------ in-game memory

    def get_context(self, game: Game) -> Dict[str, str]:
        """Memory lines for the agent prompt (rendered as '- key: value')."""
        rows = self.session.exec(
            select(AgentMemory)
            .where(AgentMemory.game_id == game.id)
            .order_by(AgentMemory.id.desc())
            .limit(RECENT_REASONINGS)
        ).all()
        context: Dict[str, str] = {}
        if rows:
            latest = rows[0]
            if latest.plan:
                context["your current plan"] = latest.plan
            reasonings = [row.reasoning for row in reversed(rows) if row.reasoning]
            if reasonings:
                context["your recent move reasonings (oldest first)"] = " | ".join(reasonings)
        hint = self.book_hint(game.current_fen)
        if hint:
            context["opening book (lines from games you won)"] = hint
        return context

    def remember(
        self, game_id: int, move_number: int, *, plan: str = "", reasoning: str = ""
    ) -> Optional[AgentMemory]:
        """Persist the agent's plan/reasoning for the move it just played.
        Minimax moves carry neither — nothing is stored for them."""
        if not plan and not reasoning:
            return None
        row = AgentMemory(
            game_id=game_id, move_number=move_number, plan=plan, reasoning=reasoning
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def forget_after(self, game_id: int, ply_count: int) -> None:
        """Drop memory of undone moves so stale plans don't haunt the prompt."""
        rows = self.session.exec(
            select(AgentMemory)
            .where(AgentMemory.game_id == game_id)
            .where(AgentMemory.move_number > ply_count)
        ).all()
        for row in rows:
            self.session.delete(row)
        if rows:
            self.session.commit()

    # ------------------------------------------------------- opening book

    def book_hint(self, fen: str) -> Optional[str]:
        """Human-readable hint for the prompt, best-scoring lines first;
        None when the book has nothing positive for this position."""
        entries = self.session.exec(
            select(OpeningBookEntry).where(
                OpeningBookEntry.position_fen == position_key(fen)
            )
        ).all()
        good = sorted(
            (e for e in entries if e.wins > e.losses),
            key=lambda e: e.wins - e.losses,
            reverse=True,
        )
        if not good:
            return None
        return ", ".join(
            f"{e.move_san} scored {e.wins} win(s) / {e.losses} loss(es) from this position"
            for e in good[:BOOK_HINTS]
        )

    def update_book(self, game: Game, moves: List[Move]) -> None:
        """Fold a finished agent game into the book (decisive results only).
        Both wins and losses are counted, so bad lines stop being suggested."""
        if game.mode != "agent" or game.result not in ("1-0", "0-1"):
            return
        agent_color = "black" if game.user_color == "white" else "white"
        agent_won = (game.result == "1-0") == (agent_color == "white")

        board = chess.Board()
        for index, move in enumerate(moves[:BOOK_PLY_LIMIT]):
            mover = "white" if index % 2 == 0 else "black"
            key = position_key(board.fen())
            try:
                board.push(board.parse_san(move.move_san))
            except ValueError:  # corrupt history — stop rather than mis-key
                return
            if mover != agent_color:
                continue
            entry = self.session.exec(
                select(OpeningBookEntry)
                .where(OpeningBookEntry.position_fen == key)
                .where(OpeningBookEntry.move_san == move.move_san)
            ).first()
            if entry is None:
                entry = OpeningBookEntry(position_fen=key, move_san=move.move_san)
            if agent_won:
                entry.wins += 1
            else:
                entry.losses += 1
            self.session.add(entry)
        self.session.commit()
