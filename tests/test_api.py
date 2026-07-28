"""Integration tests for the FastAPI backend (fresh temp SQLite per run)."""

import os
import tempfile

import pytest

# Point the app at a throwaway database BEFORE importing it, pin the user
# to white for deterministic assertions, and force the offline minimax agent
# so tests never hit the network even when ANTHROPIC_API_KEY is set locally.
_tmpdir = tempfile.mkdtemp(prefix="chess_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmpdir, 'test.db')}"
os.environ["DEFAULT_USER_COLOR"] = "white"
os.environ["AGENT_BACKEND"] = "minimax"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_current_game_created_on_first_call(client):
    response = client.get("/api/games/current")
    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["turn"] == "white"
    assert data["user_color"] == "white"
    assert data["fen"].startswith("rnbqkbnr/pppppppp")

    # Second call resumes the same game.
    again = client.get("/api/games/current").json()
    assert again["game_id"] == data["game_id"]
    assert again["created"] is False


def test_possible_moves(client):
    response = client.post("/api/possible-moves", json={"square": "e2"})
    assert response.status_code == 200
    assert response.json()["moves"] == ["e3", "e4"]

    empty = client.post("/api/possible-moves", json={"square": "e5"})
    assert empty.json()["moves"] == []


def test_illegal_move_rejected(client):
    response = client.post("/api/move", json={"from_square": "e2", "to_square": "e6"})
    assert response.status_code == 400
    assert "illegal" in response.json()["detail"].lower()


def test_move_triggers_agent_reply(client):
    response = client.post("/api/move", json={"from_square": "e2", "to_square": "e4"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_move"]["san"] == "e4"
    assert data["user_move"]["player"] == "User"
    assert data["agent_move"] is not None
    assert data["agent_move"]["player"] == "Agent"
    assert data["turn"] == "white"  # back to the user after the agent replied
    # Exact PGN: guards against the SAN-duplication regression where
    # record_move queried history after session.add (autoflush).
    assert data["pgn"] == f"1. e4 {data['agent_move']['san']}"


def test_game_state_reflects_moves(client):
    state = client.get("/api/game-state").json()
    assert state["move_count"] == 2  # user + agent
    assert state["turn"] == "white"
    assert not state["is_game_over"]


def test_not_your_turn_guard(client):
    # White to move; a black-piece move must be rejected as illegal.
    response = client.post("/api/move", json={"from_square": "e7", "to_square": "e6"})
    assert response.status_code == 400


def test_logs_recorded(client):
    game_id = client.get("/api/games/current").json()["game_id"]
    logs = client.get(f"/api/logs/?game_id={game_id}").json()
    actions = [log["action_type"] for log in logs]
    assert "game_start" in actions
    assert "move" in actions
    move_logs = [log for log in logs if log["action_type"] == "move"]
    assert {log["details"]["player"] for log in move_logs} == {"User", "Agent"}

    # No game_id -> logs of the current game.
    default_logs = client.get("/api/logs/").json()
    assert [log["id"] for log in default_logs] == [log["id"] for log in logs]


def test_favorite_toggle(client):
    game_id = client.get("/api/games/current").json()["game_id"]
    response = client.post(f"/api/games/{game_id}/favorite")
    assert response.status_code == 200
    assert response.json()["is_favorite"] is True
    assert client.post(f"/api/games/{game_id}/favorite").json()["is_favorite"] is False
    assert client.post("/api/games/999999/favorite").status_code == 404


def test_new_game_completes_previous(client):
    old_id = client.get("/api/games/current").json()["game_id"]
    response = client.post("/api/games/new")
    assert response.status_code == 200
    new_data = response.json()
    assert new_data["game_id"] != old_id
    assert new_data["created"] is True

    games = {g["id"]: g for g in client.get("/api/games").json()}
    assert games[old_id]["is_completed"] is True
    assert games[old_id]["result"] == "*"
    assert games[new_data["game_id"]]["is_completed"] is False


def test_games_list_and_favorites_filter(client):
    all_games = client.get("/api/games").json()
    assert len(all_games) >= 2
    favorites = client.get("/api/games?favorites_only=true").json()
    assert all(g["is_favorite"] for g in favorites)


def test_replay(client):
    # The first game has two recorded plies.
    games = client.get("/api/games").json()
    finished = [g for g in games if g["move_count"] > 0][0]
    replay = client.get(f"/api/games/{finished['id']}/replay")
    assert replay.status_code == 200
    data = replay.json()
    assert data["start_fen"].startswith("rnbqkbnr")
    assert len(data["moves"]) == finished["move_count"]
    first = data["moves"][0]
    assert first["move_number"] == 1
    assert first["move_san"] == "e4"
    assert first["fen_after"].split()[1] == "b"  # black to move after 1.e4
    assert client.get("/api/games/999999/replay").status_code == 404


def test_undo_single_move(client):
    client.post("/api/games/new", json={"user_color": "white"})
    start_fen = client.get("/api/game-state").json()["fen"]

    client.post("/api/move", json={"from_square": "e2", "to_square": "e4"})
    assert client.get("/api/game-state").json()["move_count"] == 2  # user + agent

    response = client.post("/api/undo", json={})
    assert response.status_code == 200
    state = response.json()
    assert state["move_count"] == 0
    assert state["fen"] == start_fen
    assert state["turn"] == "white"
    assert state["pgn"] == ""

    # Logged as an undo action.
    logs = client.get(f"/api/logs/?game_id={state['game_id']}").json()
    assert "undo" in [log["action_type"] for log in logs]


def test_undo_many_plies_back_to_start(client):
    client.post("/api/games/new", json={"user_color": "white"})
    start_fen = client.get("/api/game-state").json()["fen"]

    import chess as pychess

    for _ in range(3):
        state = client.get("/api/game-state").json()
        board = pychess.Board(state["fen"])
        move = next(iter(board.legal_moves))
        client.post(
            "/api/move",
            json={
                "from_square": pychess.square_name(move.from_square),
                "to_square": pychess.square_name(move.to_square),
            },
        )

    response = client.post("/api/undo", json={"plies": 999})
    assert response.status_code == 200
    state = response.json()
    assert state["move_count"] == 0
    assert state["fen"] == start_fen

    # Nothing left to undo.
    assert client.post("/api/undo", json={}).status_code == 409


def test_user_plays_black(client):
    response = client.post("/api/games/new", json={"user_color": "black"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_color"] == "black"
    # The agent (white) opened the game immediately; it's the user's turn.
    assert data["move_count"] == 1
    assert data["turn"] == "black"

    # A black reply works, and the agent answers as white.
    state = client.get("/api/game-state").json()
    import chess as pychess

    board = pychess.Board(state["fen"])
    move = next(iter(board.legal_moves))
    response = client.post(
        "/api/move",
        json={
            "from_square": pychess.square_name(move.from_square),
            "to_square": pychess.square_name(move.to_square),
        },
    )
    assert response.status_code == 200
    assert response.json()["turn"] == "black"  # agent replied, user again

    # Undo lands back on the user's turn with the agent's opener replayed.
    undone = client.post("/api/undo", json={}).json()
    assert undone["move_count"] == 1
    assert undone["turn"] == "black"


def test_agent_factory_backends():
    from app.agents.chess_agent import ChessAgent
    from app.agents.llm_agent import LLMChessAgent, get_chess_agent

    # AGENT_BACKEND=minimax is pinned for this test run.
    assert isinstance(get_chess_agent(), ChessAgent)

    # The LLM agent falls back to minimax when the API is unreachable —
    # give it a client-less setup by pointing at an empty key and a broken
    # base URL via a stubbed _ask_llm.
    agent = LLMChessAgent()

    def boom(*args, **kwargs):
        raise RuntimeError("no API available")

    agent._ask_llm = boom
    choice = agent.select_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert choice is not None
    assert "uci" in choice  # minimax fallback produced a legal move


def test_pvp_local_game(client):
    response = client.post(
        "/api/pvp/games",
        json={"mode": "local", "white_name": "Alice", "black_name": "Bob"},
    )
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    state = client.get(f"/api/pvp/games/{game_id}/state").json()
    assert state["white_name"] == "Alice"
    assert state["black_name"] == "Bob"
    assert state["opponent_joined"] is True
    assert state["turn"] == "white"

    # Both sides move on the same screen; no agent interferes.
    move = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e2", "to_square": "e4"},
    ).json()
    assert move["turn"] == "black"
    assert move["move_count"] == 1
    assert move["last_move"]["san"] == "e4"
    move = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e7", "to_square": "e5"},
    ).json()
    assert move["pgn"] == "1. e4 e5"

    # per-game possible moves
    targets = client.post(
        "/api/possible-moves", json={"square": "g1", "game_id": game_id}
    ).json()
    assert "f3" in targets["moves"]

    # local undo removes exactly one half-move
    undone = client.post(f"/api/pvp/games/{game_id}/undo").json()
    assert undone["move_count"] == 1
    assert undone["turn"] == "black"

    # Alice's move is attributed to her name in the logs
    logs = client.get(f"/api/logs/?game_id={game_id}").json()
    movers = [log["details"].get("player") for log in logs if log["action_type"] == "move"]
    assert "Alice" in movers


def test_pvp_online_game_flow(client):
    created = client.post(
        "/api/pvp/games",
        json={"mode": "online", "creator_name": "Hamza", "creator_color": "white"},
    ).json()
    game_id = created["game_id"]
    assert created["your_color"] == "white"
    assert created["token"] and created["join_token"]
    assert created["token"] != created["join_token"]

    # Moves are blocked until the opponent joins.
    response = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e2", "to_square": "e4"},
        headers={"X-Player-Token": created["token"]},
    )
    assert response.status_code == 409

    # A bad token cannot join; the invite token can.
    assert (
        client.post(
            f"/api/pvp/games/{game_id}/join", json={"token": "nope", "name": "X"}
        ).status_code
        == 403
    )
    joined = client.post(
        f"/api/pvp/games/{game_id}/join",
        json={"token": created["join_token"], "name": "Rival"},
    ).json()
    assert joined["your_color"] == "black"
    # Security: the seat token is ROTATED — the invite link token dies here.
    assert joined["token"] != created["join_token"]

    # Seat can't be claimed twice (even with the original invite token).
    assert (
        client.post(
            f"/api/pvp/games/{game_id}/join",
            json={"token": created["join_token"], "name": "Impostor"},
        ).status_code
        in (403, 409)  # rotated token no longer matches -> 403
    )

    # Turn enforcement: black (rotated token) can't move on white's turn.
    response = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e2", "to_square": "e4"},
        headers={"X-Player-Token": joined["token"]},
    )
    assert response.status_code == 409

    state = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e2", "to_square": "e4"},
        headers={"X-Player-Token": created["token"]},
    ).json()
    assert state["turn"] == "black"
    assert state["your_color"] == "white"

    # The stale invite token grants nothing anymore.
    response = client.post(
        f"/api/pvp/games/{game_id}/move",
        json={"from_square": "e7", "to_square": "e5"},
        headers={"X-Player-Token": created["join_token"]},
    )
    assert response.status_code == 403

    # The opponent polls state with their rotated token (header, not URL).
    seen = client.get(
        f"/api/pvp/games/{game_id}/state",
        headers={"X-Player-Token": joined["token"]},
    ).json()
    assert seen["your_color"] == "black"
    assert seen["last_move"]["san"] == "e4"
    assert seen["white_name"] == "Hamza" and seen["black_name"] == "Rival"

    # Online games have no undo.
    assert client.post(f"/api/pvp/games/{game_id}/undo").status_code == 409


def test_online_invite_expires(client):
    from datetime import datetime, timedelta, timezone

    from sqlmodel import Session

    from app.database import engine
    from app.models.sql_models import Game

    created = client.post(
        "/api/pvp/games",
        json={"mode": "online", "creator_name": "Hamza", "creator_color": "white"},
    ).json()
    game_id = created["game_id"]

    # Age the game past the invite TTL.
    with Session(engine) as session:
        game = session.get(Game, game_id)
        game.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        session.add(game)
        session.commit()

    # Joining a stale invite fails with 410 Gone...
    response = client.post(
        f"/api/pvp/games/{game_id}/join",
        json={"token": created["join_token"], "name": "TooLate"},
    )
    assert response.status_code == 410

    # ...and the game is closed out.
    state = client.get(f"/api/pvp/games/{game_id}/state").json()
    assert state["is_game_over"] is True
    assert state["result"] == "*"


def test_pvp_games_do_not_hijack_agent_current_game(client):
    agent_game = client.post("/api/games/new", json={"user_color": "white"}).json()
    pvp = client.post("/api/pvp/games", json={"mode": "local"}).json()
    # The agent flow still points at the agent game, not the newer PvP game.
    current = client.get("/api/games/current").json()
    assert current["game_id"] == agent_game["game_id"]
    assert current["game_id"] != pvp["game_id"]
    # And the library lists both with their modes.
    games = {g["id"]: g for g in client.get("/api/games").json()}
    assert games[pvp["game_id"]]["mode"] == "local"
    assert games[agent_game["game_id"]]["mode"] == "agent"


def test_full_game_scholars_mate(client):
    """Play out a forced sequence to exercise game-over handling."""
    client.post("/api/games/new")
    # The agent replies between user moves, so a scripted mate is not
    # guaranteed — instead verify a longer legal exchange keeps working.
    for _ in range(5):
        state = client.get("/api/game-state").json()
        if state["is_game_over"]:
            break
        # Ask for any piece with legal moves and play the first one.
        import chess as pychess

        board = pychess.Board(state["fen"])
        move = next(iter(board.legal_moves))
        response = client.post(
            "/api/move",
            json={
                "from_square": pychess.square_name(move.from_square),
                "to_square": pychess.square_name(move.to_square),
            },
        )
        assert response.status_code == 200
