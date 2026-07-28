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

## Logs

### `GET /api/logs/?game_id=<id>`
Log entries for the given game (current game when omitted):
`[{id, game_id, timestamp, action_type, details}]` with `action_type` one of
`game_start | resume | move | favorite_toggle | game_over`. Move entries
carry `{player, san, from, to, fen, move_number}` in `details`.

## Misc

### `GET /api/health`
`{"status": "ok"}` — used by the Docker healthcheck.
