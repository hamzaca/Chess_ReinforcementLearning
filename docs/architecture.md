# Architecture

```
┌─────────────────────┐         ┌──────────────────────────────────┐
│  Angular frontend    │  /api   │  FastAPI backend                 │
│  (nginx :4200)       ├────────►│  (uvicorn :8000)                 │
│                      │         │                                  │
│  chess-board  (Play) │         │  main.py (endpoints)             │
│  game-library        │         │   ├─ services/chess_service      │
│  replay-viewer       │         │   │    (python-chess rules/PGN)  │
│  services/chess.svc  │         │   ├─ services/game_manager (CRUD)│
└─────────────────────┘         │   ├─ services/replay_service     │
                                 │   ├─ agents/chess_agent (minimax)│
                                 │   └─ observability/logger ──┐    │
                                 │                             ▼    │
                                 │  SQLModel: Game / Move / Log     │
                                 │  SQLite (dev) / PostgreSQL (env) │
                                 └──────────────────────────────────┘
```

## Layers

- **`chess_engine/`** — in-repo, dependency-free chess library; the refactor
  of the legacy pygame engine with all bugs fixed (immutable pieces, board
  as single source of truth, full rules incl. castling/en passant/promotion,
  legal-move filtering). Perft-validated against python-chess. Reserved as
  the future RL training environment.
- **`app/services/chess_service.py`** — stateless rules facade over
  python-chess: legal-move queries, move application, SAN/PGN, game status.
  FEN in, FEN out; no state kept in memory.
- **`app/services/game_manager.py`** — game lifecycle and persistence:
  current-game lookup/creation, move recording (Move rows + Game.current_fen
  + Game.pgn), favorites, completion.
- **`app/agents/chess_agent.py`** — negamax + alpha-beta (depth 2 by
  default, `AGENT_DEPTH` env var), material + centralization evaluation,
  repetition avoidance using game history. `# TODO(RL)` marks the hook where
  a learned policy/value model plugs in.
- **`app/observability/`** — `GameLogger` persists every action to the `Log`
  table (shared request session via DI) and mirrors to console via loguru;
  `tracer.py` provides timed spans.

## Key flows

**User move** (`POST /api/move`): validate turn → apply user move
(400 if illegal) → record Move + log → if game continues, agent selects and
plays a reply (recorded + logged) → response carries both moves + new state.

**Resume** (`GET /api/games/current`): newest `is_completed=false` game or a
new one; if the server died between user move and agent reply, the agent
catches up here.

**Replay** (`GET /api/games/{id}/replay`): stored SAN list is replayed
server-side to attach `fen_after` to every ply, so the frontend can step
through positions without a chess engine.

## Persistence

SQLite by default (`sqlite:///./chess_data.db`), swappable to PostgreSQL via
`DATABASE_URL`. Schema is migrated with alembic (`alembic upgrade head`);
`init_db()` also `create_all`s at startup for dev convenience. In Docker the
SQLite file lives on the `chess-data` named volume.

## Known limitations / next steps

- Single implicit user/session — no auth (see `app/security/` placeholder).
- Frontend auto-promotes pawns to queens (backend supports under-promotion).
- The RL agent, self-play pipeline and feedback collection are not built yet.
