# Code Style Rules

## Python (backend, chess_engine)
- Python 3.11+; 4-space indent; type hints on all public functions.
- Docstrings on every module and public class/function; explain *why* for
  anything non-obvious (especially chess rules edge cases).
- Services are stateless classes with injected `Session`; no module-level
  mutable state. FastAPI wiring via `Depends`.
- Raise domain exceptions (`IllegalMoveError`) in services; translate to
  HTTP status codes only in `app/main.py`.
- Never `print()` in app code — use the loguru console logger or the DB
  `GameLogger`.
- DB access only through SQLModel sessions; timestamps are timezone-aware
  UTC via `utcnow()` in `sql_models.py`.

## TypeScript / Angular (frontend)
- Standalone components only (no NgModules); strict TypeScript.
- All backend calls go through `ChessService`; components never call
  HttpClient directly.
- Shared FEN/board helpers live in `board-utils.ts` — do not duplicate
  board-parsing logic inside components.
- Keep API DTO interfaces in `models.ts` in sync with `app/models/schemas.py`.

## General
- No top-level Python package named `chess` (shadows python-chess).
- New endpoints require: schema in `schemas.py`, service method, endpoint,
  and an integration test in `tests/test_api.py`.
