# Chess AI — FastAPI + Angular

Play chess against an AI agent in the browser, with persistent games,
favorites, full-game replay and structured logging.

Migrated from a local pygame prototype (archived in `legacy_pygame_chess/`)
into a production-style web application.

## Stack

| Layer      | Tech |
|------------|------|
| Frontend   | Angular 18 (standalone components), nginx in Docker |
| Backend    | FastAPI + SQLModel + alembic, python-chess for rules/SAN/PGN |
| AI agent   | Negamax + alpha-beta (depth 2), RL hook prepared (`# TODO(RL)`) |
| Engine lib | `chess_engine/` — in-repo, dependency-free, perft-validated; future RL environment |
| Database   | SQLite (dev) / PostgreSQL via `DATABASE_URL` |

## Quick start (Docker)

```bash
docker compose up --build
# frontend: http://localhost:4200   backend docs: http://localhost:8000/docs
```

Game data persists on the `chess-data` volume.

## Local development

Backend (Python ≥ 3.11):

```bash
pip install -e ".[dev]"
alembic upgrade head          # or rely on startup create_all in dev
uvicorn app.main:app --reload # http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm start                     # http://localhost:4200, proxies /api to :8000
```

Tests / seed data:

```bash
python -m pytest              # engine perft + API integration tests
python scripts/seed.py        # adds a sample completed game
```

## Features

- **Play vs agent** — which side you play is random per game (White always
  moves first; when the agent gets White it opens immediately). The board
  flips so your pieces are at the bottom, and it resumes exactly where you
  left off (`GET /api/games/current` + stored FEN).
- **Undo** — take back your last move, or rewind all the way to the start
  (`POST /api/undo`).
- **Two players** — play a friend on the same screen, or create an online
  game and send them the invite link (each player gets a secret seat token;
  the opponent's board updates by polling). Player names are shown above the
  board with the active side highlighted.
- **LLM agent (optional)** — copy `.env.example` to `.env` and set
  `ANTHROPIC_API_KEY` to have Claude (`claude-opus-5`) pick the agent's
  moves using the game context (FEN + PGN history + legal moves), with a
  pydantic-validated structured response. Without a key (or on any API
  failure) the local minimax agent plays instead.
- **Show Legal Moves toggle** — highlighted destinations on click, or free
  clicking with server-side rejection of illegal moves.
- **Game library** — all games with favorite stars (`?favorites_only=true`),
  start-new-game, replay.
- **Replay viewer** — step through any stored game move by move.
- **Logging** — every action (game_start, resume, move, favorite_toggle,
  game_over) is persisted to the `Log` table; `GET /api/logs/?game_id=…`.

## Project layout

```
app/            FastAPI backend (models, services, agents, observability)
chess_engine/   Fixed, importable chess library (future RL environment)
frontend/       Angular app (chess-board, game-library, replay-viewer)
alembic/        Database migrations
scripts/        seed / migrate / healthcheck
tests/          engine perft tests + API integration tests
docs/           architecture + API reference
claude/         AI-agent project memory and coding rules
legacy_pygame_chess/  original prototype (superseded, kept for reference)
```

## The legacy engine bugs (all fixed in `chess_engine/`)

1. `get_color` property called as a function → crash. Now plain attributes.
2. Missing `EmptyCell` import in `Game.py` → `NameError`. Class eliminated.
3. Pawn direction tied to player seating instead of color.
4. Captures left stale piece coordinates. Pieces are now immutable and
   coordinate-free; the board is the single source of truth.
5. Checkmate simulation reused stale piece objects. Replaced with board-copy
   legality filtering.
6. No castling, en passant, promotion, or pin/check legality. All
   implemented and perft-validated against python-chess.
