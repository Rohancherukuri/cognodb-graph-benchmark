#!/usr/bin/env bash
# Starts the self-hosted comparison databases (Memgraph, ArangoDB, Dgraph),
# each resource-capped in docker-compose.yml to match CognoDB's free tier.
set -euo pipefail
echo "Starting self-hosted comparison databases (memgraph, arangodb, dgraph)..."
docker compose up -d memgraph arangodb dgraph
docker compose ps
echo
echo "Waiting a few seconds for the databases to finish initializing..."
sleep 10
echo "Ready. Next: 'make dataset' then 'make bench'."
