#!/usr/bin/env bash
# One-shot: prepare dataset -> run every enabled platform -> build report.
# Requires: infra already started (scripts/start_infra.sh) and .env filled in
# with CognoDB / Neo4j Aura credentials.
set -euo pipefail
benchmark dataset prepare --source snap --target-edges "${DATASET_TARGET_EDGES:-300000}"
benchmark bench run --platform all
benchmark report
echo
echo "Done. See results/REPORT.md and results/*.json"
