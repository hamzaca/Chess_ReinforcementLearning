# API Reference

Base URL: `/api`. Interactive docs at `http://localhost:8000/docs`.
Squares use algebraic notation (`"e2"`). White always moves first, but which
side the human plays is decided per game (random by default) — every state
response carries `user_color`. When the agent owns White it opens the game
automatically.

## Games

### `GET /api/games/current`
Most recent unfinished game; creates one if none exists. If it is Black's
turn (server restarted mid-exchange) the agent moves first.
Returns `{game_id, fen, turn, pgn, created, in_check, is_game_over, result}`.

### `POST /api/games/new`
Marks the current game completed (`result "*"`) and creates a fresh one.
Optional body `{"user_color": "white" | "black" | "random"}` — omitted uses
the configured default (random). Same response shape as above with
`created: true`; if the agent got White its opening move is already played.

### `GET /api/games?favorites_only=true|false`
All games, newest first: `[{id, created_at, updated_at, is_completed,
result, is_favorite, move_count}]`.

### `POST /api/games/{id}/favorite`
Toggles the favorite flag. Returns `{game_id, is_favorite}`. 404 if unknown.

### `GET /api/games/{id}/replay`
`{game_id, pgn, start_fen, moves: [{move_number, from_square, to_square,
move_san, fen_after}]}` sorted by move number. `fen_after` lets clients step
through positions without their own engine. 404 if unknown.

## Game play

### `GET /api/game-state`
State of the current game: `{game_id, fen, turn, pgn, in_check,
is_game_over, result, move_count}`.

### `POST /api/move`
Body: `{from_square, to_square, promotion?}` (`promotion` in `q|r|b|n`,
defaults to queen for a promoting pawn move).
Applies the user's move, then the agent's reply.
Returns `{user_move, agent_move, fen, turn, pgn, in_check, is_game_over,
result}` where each move is `{from_square, to_square, san, player}`.
Errors: `400` illegal move, `409` game over / not your turn.

### `POST /api/undo`
Body: `{"plies": n}` (optional). Takes back the user's last move (plus the
agent reply after it); an explicit ply count rewinds at least that far — a
large value rewinds to the start of the game. Always lands on the user's
turn (if the rewind lands on the agent's turn, e.g. undo-to-start while
playing Black, the agent replays its move). Reopens a finished game.
Returns the same shape as `/api/game-state`. `409` when nothing to undo.
Logged as action `undo`.

### `POST /api/abort`
Aborts the current agent game: no winner, `result "*"`, logged as
`game_over` with reason `aborted_by_user`. `409` when no game is running.
Returns the final game state.

### `POST /api/possible-moves`
Body: `{square}`. Returns `{square, moves: ["e3", "e4", ...]}` — legal
destinations from that square in the current game (empty for empty squares
or opponent pieces).

## Two players

### `POST /api/pvp/games`
Create a two-player game.
- `{"mode": "local", "white_name"?, "black_name"?}` — both players on one
  screen. Returns `{game_id, mode}`.
- `{"mode": "online", "creator_name"?, "creator_color": "white"|"black"|"random"}`
  — returns `{game_id, your_color, token, join_token}`. `token` is your seat
  secret; the frontend builds the invite link `/join/{game_id}/{join_token}`.

### `POST /api/pvp/games/{id}/join`
Body `{token, name}` — claims the free seat using the invite token.
**The invite token is single-use**: the response carries a freshly rotated
seat token (`{game_id, your_color, token}`) and the invite token stops
working. `403` bad token, `409` seat taken, `410` invite expired
(unclaimed invites die after `INVITE_TTL_HOURS`, default 24).

### `GET /api/pvp/games/{id}/state`
Seat token goes in the **`X-Player-Token` header** (never in the URL).
Full PvP state: fen/turn/pgn/result plus `white_name`, `black_name`,
`your_color` (derived from the token), `opponent_joined`, `last_move`.
Online clients poll this (~2s) to see the opponent's moves.

### `POST /api/pvp/games/{id}/move`
Body `{from_square, to_square, promotion?}`; online games authenticate via
the `X-Player-Token` header. Local games: whoever is to move plays. Online
games: the token must belong to the side to move (`403` unknown token,
`409` not your turn / opponent not joined yet). Returns the updated state.

### `POST /api/pvp/games/{id}/undo`
Local games only — takes back exactly one half-move. `409` for online games.

### `POST /api/pvp/games/{id}/abort`
Ends the game with no winner (`result "*"`). Local games abort from the
shared screen; online games require a seated player's `X-Player-Token`
(`403` otherwise). The opponent sees the aborted state on their next poll.
`409` if the game is already over.

## Logs

### `GET /api/logs/?game_id=<id>`
Log entries for the given game (current game when omitted):
`[{id, game_id, timestamp, action_type, details}]`.

`action_type` catalog (see `app/observability/logger.py::ACTIONS`):
`game_start | resume | move | agent_move | undo | abort | game_over |
favorite_toggle | player_join | invite_expired | unauthorized`.

Every entry's `details` carries:
- `status`: `success` | `failed` (rejected attempts are logged too, with a
  `reason` such as `illegal_move`, `not_your_turn`, `seat_taken`,
  `invalid_player_token`, `nothing_to_undo`) | `ongoing` (`agent_move` marks
  the agent starting to think; the following `move` entry concludes it).
- `actor`: who did it — `{"type": "user", "name"}`,
  `{"type": "player", "name", "color"}` (PvP),
  `{"type": "agent", "name", "model"}` where `model` is the engine that
  actually produced the move (`minimax(depth=2)` or `llm:<LLM_MODEL>` —
  an LLM fallback is reported as minimax), or `{"type": "system"}`.
- `player`: flat actor name (handy for quick filtering).
- action-specific data (`san`, `from`, `to`, `fen`, `move_number`, `result`,
  `reason`, ...). LLM agent moves additionally carry `reasoning` and `plan`
  (the agent's rolling strategic plan — also persisted to the
  `agent_memory` table and fed back into its next prompt).

**Access log — every endpoint call is persisted.** An HTTP middleware writes
one `api_call` entry for EVERY `/api/*` request (reads, writes and errors
alike) with `{endpoint, method, path, status_code, duration_ms, query}` and
`status: success|failed`; PvP routes carry their `game_id`. Fetch them with
`GET /api/logs/?scope=all&limit=N` (newest first, default 500). Domain
actions (`move`, `undo`, ...) are logged separately by the endpoints, so a
user move produces both an `api_call` row and a `move` row.

Note: online PvP clients poll state every ~2s, so `api_call` rows accumulate
quickly — prune the `log` table periodically if that becomes a concern.

## Agent memory (internal, no endpoints)

The LLM agent remembers within and across games — all in the regular SQL
database (no vector store; every lookup is exact-key):

- **In-game** (`agent_memory` table): each LLM move stores its `plan` and
  `reasoning`; the next prompt gets the latest plan + the last 3 reasonings,
  so play stays coherent across moves and server restarts. Undo prunes
  memory past the rewind point.
- **Opening book** (`opening_book` table): decisive agent games fold the
  agent's first ~10 moves into per-position win/loss counts (clock-stripped
  FEN keys, so transpositions collapse). Lines with a positive score are
  offered to the LLM as a prompt hint — never played blindly.

The agent itself talks to any OpenAI-compatible endpoint (`LLM_BASE_URL`,
`LLM_MODEL`, `ANTHROPIC_API_KEY` as bearer token); illegal or malformed
replies are retried up to 2 times with the exact error fed back, then the
local minimax takes over so a game can never stall.

## Misc

### `GET /api/health`
`{"status": "ok"}` — used by the Docker healthcheck.
