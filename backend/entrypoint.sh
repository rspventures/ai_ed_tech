#!/usr/bin/env bash
# Container entrypoint: apply DB migrations, then run the given command.
# Alembic owns the schema (Phase 1) — this replaces the old startup create_all
# + hand-run SQL migrations.
set -euo pipefail

echo "[entrypoint] running: alembic upgrade head"
alembic upgrade head

echo "[entrypoint] starting: $*"
exec "$@"
