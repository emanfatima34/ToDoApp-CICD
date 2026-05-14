#!/usr/bin/env bash
# Use docker-compose (v1) or docker compose (v2 plugin) — whichever exists on the Jenkins host.
set -e
if command -v docker-compose >/dev/null 2>&1; then
  exec docker-compose "$@"
fi
if docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi
echo "Error: install Docker Compose v1 (docker-compose) or v2 (docker compose plugin)." >&2
exit 1
