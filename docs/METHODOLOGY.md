# Methodology

This document maps each rule in the assignment brief (sections 3 and 5.3) to
how this repository implements it.

## Resource parity ("same resources everywhere")

CognoDB's free tier is the ceiling: burstable 0.5 vCPU, 256 MB RAM, 1 GB
disk. Every other platform is held to the same envelope:

| Platform | How parity is enforced |
|---|---|
| CognoDB Cloud | Free tier (c0), as provisioned. |
| Neo4j AuraDB | Free tier, which ships at the same order-of-magnitude spec (shared vCPU, small RAM). Exact instance specs are pulled from the Aura console and recorded in `results/*.json` / the README results table. |
| Memgraph, ArangoDB, Dgraph | Self-hosted via `docker-compose.yml`, each container capped with `cpus: 0.5` and `mem_limit: 256m` — Docker enforces this at the cgroup level, so it isn't just advisory. |

The assignment explicitly allows this: *"Free tiers, free trials or
self-hosted deployments capped to the same resources are all fine."*
Advertised specs for every platform are recorded per-run in
`config/platforms.yaml` → `platform_specs`, and echoed into every result
file so the README table is generated from real config, not hand-typed.

## Same dataset, same queries everywhere

- `benchmark dataset prepare` produces one `nodes.csv` / `edges.csv` pair
  and a `manifest.json` (source, counts, sha256) used, unmodified, as input
  to every adapter's `load_nodes` / `load_edges`.
- Every adapter implements the exact same `GraphDBAdapter` interface
  (`src/benchmark/adapters/base.py`). The orchestrator (`orchestrator.py`)
  calls the same six operations, in the same order, with the same sampled
  start-node IDs (seeded via `random_seed`), against every platform. Only
  the query *language* differs per platform (Cypher / AQL / DQL) — the
  logical operation (e.g. "count distinct nodes reachable in exactly N
  hops") is identical.

## Warm-up and iteration counts

`orchestrator.run_platform` runs a short warm-up pass (point lookups on
~10% of the sample) before any latency is recorded, then executes each read
workload `iterations` times (default 100, configurable via
`BENCHMARK_ITERATIONS`) and reports p50/p95/p99 via
`metrics/stats.summarize`, not just an average.

## Mixed workload / concurrency sweep

`concurrency_levels` (default `[1, 10, 40]`) is swept via a
`ThreadPoolExecutor`; each worker thread hammers `adapter.mixed_op(...)`
for `mixed_duration_seconds` with a configurable read/write ratio
(default 80/20), and QPS is `total_ops / duration`.

## Honest caveats

`run_platform` wraps the whole per-platform run in `try/except`: a failure
on one platform (timeout, auth error, unsupported query) is caught, logged,
and recorded as a caveat string in that platform's result JSON — the run
continues for the remaining platforms instead of aborting. Anything the
harness could not measure (e.g. footprint/memory on a managed free tier
that doesn't expose it) is reported as `"note": "not observable"` rather
than guessed.

## What still requires a human judgment call

- **Dataset choice**: `dataset prepare --source snap` samples SNAP
  soc-Pokec by default; swap in a different public dataset by adding a new
  `dataset/*.py` loader that emits the same `nodes.csv`/`edges.csv` shape.
- **Cold vs. warm numbers**: the harness reports warm numbers by design
  (warm-up pass before measurement). If you want cold-start numbers too,
  run `benchmark bench run` immediately after `docker compose up` /
  right after provisioning the cloud instance, before any warm-up, and
  label that run separately in the README.
- **Variance across repeated runs**: re-run `benchmark bench run` multiple
  times and diff the JSON files to report run-to-run variance — the
  harness itself always overwrites `results/<platform>.json` with the
  latest run, so copy prior runs elsewhere first if you want to keep them.
