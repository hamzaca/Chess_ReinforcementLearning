#!/usr/bin/env sh
# Apply database migrations. Run from the repository root.
# DATABASE_URL can be exported first to target PostgreSQL.
set -e
alembic upgrade head
echo "Migrations applied."
