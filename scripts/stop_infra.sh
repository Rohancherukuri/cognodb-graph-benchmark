#!/usr/bin/env bash
# Stops and removes the self-hosted comparison databases and their containers.
# Data inside them is NOT preserved (fresh state next time, which is what we
# want for a fair, reproducible re-run).
set -euo pipefail
echo "Stopping and removing self-hosted comparison databases..."
docker compose down
echo "Stopped."
