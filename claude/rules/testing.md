# Testing Rules

- Run everything with `python -m pytest` from the repo root.
- **chess_engine changes** must keep the perft cross-validation tests green
  (`tests/test_chess_engine.py`). If you touch move generation, add a perft
  case or a python-chess comparison for the rule you changed — hand-listed
  move sets are not acceptable as the only evidence.
- **API changes** get integration tests in `tests/test_api.py` using
  FastAPI's TestClient against a throwaway SQLite DB (see the `DATABASE_URL`
  override at the top of that file — it must run before importing `app`).
- Every fixed bug gets a regression test named `test_bug<N>_...` or a
  descriptive equivalent, with a comment stating what used to break.
- Tests must not depend on the agent picking a specific move (the search is
  deterministic today, but treat it as an implementation detail).
- No network, no real time dependencies, no sleeping in tests.
