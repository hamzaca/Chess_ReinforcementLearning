# Chess AI — Project Memory

## What this is
Web chess app where a user plays White against an AI agent: FastAPI backend +
Angular frontend + SQLModel/SQLite persistence, migrated from a legacy pygame
prototype (archived in `legacy_pygame_chess/` — do not build on it).

## Architecture decisions (do not silently reverse)
- **Two chess implementations, on purpose.**
  - `chess_engine/`: in-repo, dependency-free engine (refactor of the legacy
    code with all bugs fixed). Intended as the future RL environment.
    Cross-validated against python-chess via perft tests.
  - `python-chess` (`import chess`): the authoritative rules/SAN/PGN engine
    used by `app/services/chess_service.py` for production validation.
- **Never create a top-level package named `chess`** — it would shadow
  python-chess. That is why the legacy folder was renamed.
- Which side the user plays is random per game (`Game.user_color`,
  `DEFAULT_USER_COLOR` env var; tests pin it to white). White always moves
  first. `/api/games/current`, `/api/games/new` and `/api/undo` auto-play
  the agent whenever it is the agent's turn.
- Agent backends: `app/agents/chess_agent.py` (minimax) and
  `app/agents/llm_agent.py` (Claude via anthropic SDK, structured output
  parsed into a pydantic model, minimax fallback). Selected by
  `AGENT_BACKEND` / `ANTHROPIC_API_KEY` in `.env` — tests force
  `AGENT_BACKEND=minimax` so they never hit the network.
- All game state lives in the DB (`Game.current_fen`, `Move` rows).
  Services are stateless; FEN in, FEN out.
- Every state change is logged to the `Log` table via
  `app/observability/logger.py` (actions: game_start, resume, move,
  favorite_toggle, game_over).

## RL hook
`app/agents/chess_agent.py` is minimax (depth from `AGENT_DEPTH` env var).
The `# TODO(RL)` markers show where a policy/value network replaces the
hand-crafted evaluation and search.

## Commands
- Backend dev:   `uvicorn app.main:app --reload` (repo root)
- Frontend dev:  `cd frontend && npm start` (proxies /api to :8000)
- Tests:         `python -m pytest`
- Migrations:    `alembic upgrade head` / `alembic revision --autogenerate`
- Full stack:    `docker compose up --build`
- Seed demo data: `python scripts/seed.py`

## Rules
See `claude/rules/` for code style and testing rules.
