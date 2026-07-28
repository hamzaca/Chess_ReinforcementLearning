"""Unit tests for the LLM chess agent (mocked client — never hits a server)
and the agent memory service (in-memory SQLite)."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.agents.llm_agent import LLMChessAgent, _extract_json
from app.models.sql_models import AgentMemory, Game, Move, OpeningBookEntry
from app.services.agent_memory import AgentMemoryService, position_key

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def decision(move_san: str, reasoning: str = "because", plan: str = "develop pieces") -> str:
    return json.dumps({"move_san": move_san, "reasoning": reasoning, "plan": plan})


class FakeCompletions:
    """Stands in for client.chat.completions; replays canned replies."""

    def __init__(self, replies, reject_response_format: bool = False):
        self.replies = list(replies)
        self.calls = []
        self.reject_response_format = reject_response_format

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.reject_response_format and "response_format" in kwargs:
            raise RuntimeError("response_format is not supported")
        content = self.replies.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def make_agent(replies, **fake_kwargs) -> LLMChessAgent:
    agent = LLMChessAgent(model="test-model")
    fake = FakeCompletions(replies, **fake_kwargs)
    agent._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return agent


def completions_of(agent: LLMChessAgent) -> FakeCompletions:
    return agent._client.chat.completions


# ------------------------------------------------------------- move choice


def test_happy_path_returns_llm_move_with_plan():
    agent = make_agent([decision("e4", plan="control the center")])
    move = agent.select_move(START_FEN)
    assert move["from_square"] == "e2"
    assert move["to_square"] == "e4"
    assert move["engine"] == "llm:test-model"
    assert move["plan"] == "control the center"
    assert len(completions_of(agent).calls) == 1


def test_illegal_move_retried_with_feedback():
    agent = make_agent([decision("Nxe5"), decision("e4")])  # Nxe5 illegal at start
    move = agent.select_move(START_FEN)
    assert move["to_square"] == "e4"
    assert move["engine"] == "llm:test-model"
    calls = completions_of(agent).calls
    assert len(calls) == 2
    feedback = calls[1]["messages"][-1]["content"]
    assert "Nxe5" in feedback and "rejected" in feedback


def test_garbage_after_retries_falls_back_to_minimax():
    agent = make_agent(["not json at all"] * 5)
    move = agent.select_move(START_FEN)
    assert move is not None
    assert move["engine"].startswith("minimax")


def test_fenced_json_is_parsed():
    fenced = f"```json\n{decision('e4')}\n```"
    agent = make_agent([fenced])
    assert agent.select_move(START_FEN)["to_square"] == "e4"


def test_uci_accepted_when_san_parse_fails():
    agent = make_agent([decision("e2e4")])
    move = agent.select_move(START_FEN)
    assert move["uci"] == "e2e4"
    assert move["engine"] == "llm:test-model"


def test_response_format_rejection_downgrades_gracefully():
    agent = make_agent([decision("e4")], reject_response_format=True)
    move = agent.select_move(START_FEN)
    assert move["to_square"] == "e4"
    calls = completions_of(agent).calls
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]
    assert agent._response_format_ok is False


def test_memory_context_rendered_into_prompt():
    agent = make_agent([decision("e4")])
    agent.select_move(START_FEN, context={"your current plan": "attack the king"})
    prompt = completions_of(agent).calls[0]["messages"][-1]["content"]
    assert "attack the king" in prompt


def test_extract_json_finds_object_in_prose():
    assert _extract_json('Sure! Here it is: {"a": 1} hope that helps') == '{"a": 1}'


# ------------------------------------------------------------ memory store


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def make_game(session, *, user_color="white", mode="agent", fen=START_FEN, result=None):
    game = Game(current_fen=fen, user_color=user_color, mode=mode, result=result)
    session.add(game)
    session.commit()
    session.refresh(game)
    return game


def add_moves(session, game, sans):
    for i, san in enumerate(sans, start=1):
        session.add(
            Move(game_id=game.id, move_number=i, from_square="-", to_square="-", move_san=san)
        )
    session.commit()
    return [m for m in session.exec(select(Move).order_by(Move.move_number)).all()]


def test_remember_and_get_context_roundtrip(session):
    game = make_game(session)
    memory = AgentMemoryService(session)
    memory.remember(game.id, 2, plan="fianchetto the bishop", reasoning="solid setup")
    memory.remember(game.id, 4, plan="push the h-pawn", reasoning="open the file")

    context = memory.get_context(game)
    assert context["your current plan"] == "push the h-pawn"
    assert "solid setup" in context["your recent move reasonings (oldest first)"]
    # Minimax moves (no plan, no reasoning) are not stored at all.
    assert memory.remember(game.id, 6) is None


def test_forget_after_prunes_undone_moves(session):
    game = make_game(session)
    memory = AgentMemoryService(session)
    memory.remember(game.id, 2, plan="old plan", reasoning="r1")
    memory.remember(game.id, 4, plan="newer plan", reasoning="r2")
    memory.forget_after(game.id, 2)

    rows = session.exec(select(AgentMemory)).all()
    assert [r.move_number for r in rows] == [2]
    assert memory.get_context(game)["your current plan"] == "old plan"


FOOLS_MATE = ["f3", "e5", "g4", "Qh4#"]  # black wins, "0-1"


def test_book_built_from_agent_win(session):
    game = make_game(session, user_color="white", result="0-1")  # agent played black
    moves = add_moves(session, game, FOOLS_MATE)
    memory = AgentMemoryService(session)
    memory.update_book(game, moves)

    entries = session.exec(select(OpeningBookEntry)).all()
    assert {(e.move_san, e.wins, e.losses) for e in entries} == {("e5", 1, 0), ("Qh4#", 1, 0)}

    # The hint keys on the position the move was played FROM (after 1. f3).
    fen_after_f3 = "rnbqkbnr/pppppppp/8/8/8/5P2/PPPPP1PP/RNBQKBNR b KQkq - 0 1"
    hint = memory.book_hint(fen_after_f3)
    assert hint is not None and "e5" in hint

    # And it lands in the agent context for a game standing at that position.
    game2 = make_game(session, fen=fen_after_f3)
    assert "e5" in memory.get_context(game2)["opening book (lines from games you won)"]


def test_book_records_losses_and_hides_bad_lines(session):
    game = make_game(session, user_color="black", result="0-1")  # agent played white, lost
    moves = add_moves(session, game, FOOLS_MATE)
    memory = AgentMemoryService(session)
    memory.update_book(game, moves)

    entries = session.exec(select(OpeningBookEntry)).all()
    assert {(e.move_san, e.wins, e.losses) for e in entries} == {("f3", 0, 1), ("g4", 0, 1)}
    assert memory.book_hint(START_FEN) is None  # losing lines are never suggested


def test_book_ignores_draws_aborts_and_pvp(session):
    memory = AgentMemoryService(session)
    for kwargs in ({"result": "1/2-1/2"}, {"result": "*"}, {"result": "1-0", "mode": "local"}):
        game = make_game(session, **kwargs)
        moves = add_moves(session, game, ["e4"])
        memory.update_book(game, moves)
    assert session.exec(select(OpeningBookEntry)).all() == []


def test_position_key_strips_clocks():
    assert position_key(START_FEN) == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
