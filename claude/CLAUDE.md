# Chess AI — Project Memory

## What this is
Web chess app: FastAPI backend + Angular frontend + SQLModel/SQLite
persistence, migrated from a legacy pygame prototype (archived in
`legacy_pygame_chess/` — do not build on it). Three game modes:
vs AI agent, local two-player (one screen), and online two-player
(invite link).

## Architecture decisions (do not silently reverse)
- **Two chess implementations, on purpose.**
  - `chess_engine/`: in-repo, dependency-free engine (refactor of the legacy
    code with all bugs fixed). Intended as the future RL environment.
    Cross-validated against python-chess via perft tests.
  - `python-chess` (`import chess`): the authoritative rules/SAN/PGN engine
    used by `app/services/chess_service.py` for production validation.
- **Never create a top-level package named `chess`** — it would shadow
  python-chess. That is why the legacy folder was renamed.
- All game state lives in the DB (`Game.current_fen`, `Move` rows).
  Services are stateless; FEN in, FEN out. Schema evolves via alembic
  (currently 0001_initial → 0002_user_color → 0003_pvp_games →
  0004_agent_memory).

## Game modes (`Game.mode`)
- **agent** — human vs AI. Which side the user plays is random per game
  (`Game.user_color`, `DEFAULT_USER_COLOR` env var; tests pin it to white).
  White always moves first. `/api/games/current`, `/api/games/new` and
  `/api/undo` auto-play the agent whenever it is the agent's turn.
  The implicit "current game" (`get_current_game`) is agent-mode ONLY —
  PvP games are addressed by id and must never hijack it.
- **local** — two players, one screen; whoever is to move plays; undo takes
  back exactly one half-move.
- **online** — creator picks a side; opponent joins via invite link
  (`/join/{game_id}/{join_token}`). Opponent's board updates by 2s polling.
  No undo (would need consent). Any seated player can abort.

## PvP security model (keep these invariants)
- Per-seat secrets (`Game.white_token/black_token`, `secrets.token_urlsafe(16)`).
- **Invite tokens are single-use**: `/join` rotates the claimed seat's token
  and returns the fresh one; the link token dies at claim time.
- Seat tokens travel in the **`X-Player-Token` header**, never in URLs or
  bodies; the frontend keeps them in sessionStorage (`pvp-token-store.ts`)
  and scrubs any token query params from the address bar.
- Unclaimed online invites expire after `INVITE_TTL_HOURS` (default 24),
  enforced lazily in `_pvp_game_or_404` → join returns 410.
- Deliberately deferred: rate limiting, spectator lock-down, real auth
  (`app/security/` placeholder). HTTPS is mandatory at deployment.

## Agent backends
`app/agents/chess_agent.py` (negamax minimax, depth from `AGENT_DEPTH`) and
`app/agents/llm_agent.py` — the LLM agent speaks the **OpenAI-compatible
chat API** (openai SDK) so it works against the user's local server
(`LLM_BASE_URL=http://127.0.0.1:8317/v1`, an explicit user decision) or
Anthropic's OpenAI-compat endpoint (the default). `ANTHROPIC_API_KEY` is the
bearer token; `LLM_MODEL` the server-side tag. Robustness ladder (keep it):
tolerant JSON parsing (fences/prose stripped; `response_format` dropped if
the server rejects it) → up to 2 retries with the exact error fed back
(UCI accepted as SAN fallback) → minimax fallback on ANY failure so a game
never stalls. Selected by `AGENT_BACKEND` (`auto|minimax|llm`) — tests force
`AGENT_BACKEND=minimax` so they never hit the network. Each move's dict
carries `engine` naming the engine that actually produced it; logs use it.

## Agent memory (`app/services/agent_memory.py`)
Plain SQL tables, deliberately no vector store (lookups are exact-key):
- `agent_memory`: per LLM move, its `plan` + `reasoning`; the next prompt
  gets the latest plan + last 3 reasonings. `undo_moves` prunes rows past
  the rewind point (`forget_after`).
- `opening_book`: `finish_game` folds decisive agent games into
  per-position win/loss counts (clock-stripped FEN via `position_key`, so
  transpositions collapse). Positive lines become a prompt HINT — the book
  never bypasses the LLM.

## Logging (`app/observability/logger.py`)
- `ACTIONS` catalog: game_start, resume, move, agent_move, undo, abort,
  game_over, favorite_toggle, player_join, invite_expired, unauthorized,
  api_call. Keep it in sync when adding endpoints.
- Every persisted entry's `details` has `status` (success|failed|ongoing),
  structured `actor` ({type: user|player|agent|system, name, model?, color?})
  and a flat `player` name. Failed attempts (illegal move, bad token,
  seat taken, nothing to undo) are logged too.
- An HTTP middleware in `main.py` persists an `api_call` row for EVERY
  /api/* request (endpoint, method, status_code, duration_ms) — this was an
  explicit user decision, do not remove to "optimize"; prune old rows
  instead if volume becomes a problem. `GET /api/logs/?scope=all` reads them.

## RL hook
`# TODO(RL)` markers in `app/agents/chess_agent.py` show where a
policy/value network replaces the hand-crafted evaluation and search;
`chess_engine/` is the intended training environment.

## Commands
- Backend dev:   `uvicorn app.main:app --reload` (repo root)
- Frontend dev:  `cd frontend && npm start` (proxies /api to :8000)
- Tests:         `python -m pytest` (65 tests; API tests pin env vars at import)
- Migrations:    `alembic upgrade head` / `alembic revision --autogenerate`
- Full stack:    `docker compose up --build`
- Seed demo data: `python scripts/seed.py`

## Conventions & gotchas
- `.env` holds secrets (gitignored; `.env.example` documents the keys).
- `claude/` is currently gitignored by user choice (local-only context).
- Frontend: standalone Angular components; all HTTP via `ChessService`;
  board helpers in `board-utils.ts`; PvP tokens via `pvp-token-store.ts`.
- New endpoints require: schema in `schemas.py`, service/manager method,
  endpoint, integration test, api-reference.md entry — and they are
  access-logged automatically by the middleware.

## Rules
See `claude/rules/` for code style and testing rules.
