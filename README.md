# CognoDB Cloud Graph Database Benchmark

A reproducible, honest benchmark comparing [CognoDB Cloud](https://console.cognodb.com)
against four other managed/self-hosted graph database platforms, on
identical data, identical logical queries, and matched hardware limits.

> **Status of results in this README:** the tables below are templates.
> This repo ships a complete, tested harness, but producing real numbers
> requires live accounts on each platform (see [Setup](#setup)) and a real
> run of `make bench`. Fill the tables in from `results/REPORT.md` after
> that run, then commit `results/*.json` and `results/REPORT.md` as the
> evidence backing this README.

## Why these five platforms

| Platform | Why it's here |
|---|---|
| **CognoDB Cloud** | The platform under evaluation. |
| **Neo4j AuraDB Free** | CognoDB's own setup instructions point at the official Neo4j Bolt driver — Aura is the most direct, apples-to-apples comparison since both are exercised through identical Cypher queries over the identical driver. |
| **Memgraph** | Also Bolt/Cypher-compatible, but a different storage/execution engine (in-memory, C++ core). Self-hosted so it can be pinned to *exactly* CognoDB's free-tier resource envelope via Docker, rather than trusting a third-party free tier's actual allocation. |
| **ArangoDB** | A genuinely different data model (multi-model, AQL) and query planner, self-hosted with the same resource cap. |
| **SurrealDB** | A genuinely different storage model again (multi-model, native record-graph edges via `RELATE`), queried in SurrealQL over a WebSocket RPC protocol (vs. Bolt/HTTP), self-hosted with the same resource cap. |

Two managed free tiers + three resource-capped self-hosted platforms keeps
the comparison genuinely apples-to-apples: every self-hosted platform gets
an *identical, enforced* Docker resource limit instead of an unverifiable
"free tier" claim, while the two managed platforms are directly comparable
to each other via the same driver and query language.

## Fairness / resource parity

| Platform | vCPU | RAM | Disk | Tier / enforcement |
|---|---|---|---|---|
| CognoDB Cloud | 0.5 | 256 MB | 1 GB | Free (c0), as provisioned |
| Neo4j AuraDB | 0.5 | 256 MB | 1 GB | AuraDB Free — verify against your instance in the console and correct `config/platforms.yaml` if it differs |
| Memgraph | 0.5 | 256 MB | 1 GB | `docker-compose.yml`: `cpus: 0.5`, `mem_limit: 256m` |
| ArangoDB | 0.5 | 256 MB | 1 GB | `docker-compose.yml`: `cpus: 0.5`, `mem_limit: 256m` |
| SurrealDB | 0.5 | 256 MB | 1 GB | `docker-compose.yml`: `cpus: 0.5`, `mem_limit: 256m` |

See `docs/METHODOLOGY.md` for the full rationale and how every rule in the
assignment brief maps to code.

## Dataset

Default: a sample of the [SNAP soc-Pokec social network](https://snap.stanford.edu/data/soc-Pokec.html),
sized to `DATASET_TARGET_EDGES` (default 300,000) relationships, which sits
inside the assignment's 100k–500k target range. Exact node/relationship
counts and a sha256 of the generated CSVs are written to
`data/processed/manifest.json` on every run — copy those numbers into this
section once you've run it for real:

- **Source:** `[fill in from manifest.json]`
- **Nodes:** `[N]`
- **Relationships:** `[N]`
- **Load method:** identical CSV → driver-batched `UNWIND`/`insert_many`/mutation calls per platform (see `docs/METHODOLOGY.md`)

If SNAP is unreachable (e.g. no internet in a CI sandbox), `dataset prepare`
automatically falls back to a seeded synthetic scale-free graph so the
harness stays runnable end-to-end — this is clearly labeled in the manifest
and is **not** a substitute for the real dataset in your actual submission.

## Repository layout

See `PROJECT_STRUCTURE.txt` for the full tree. In short:

```
src/benchmark/adapters/    one file per platform driver, all implementing
                            the same GraphDBAdapter interface
src/benchmark/dataset/     SNAP downloader + synthetic fallback + prepare CLI
src/benchmark/metrics/     percentile stats, result dataclasses, report builder
src/benchmark/orchestrator.py   runs the full workload sequence per platform
src/benchmark/cli.py       `benchmark` command (dataset / bench / report)
config/platforms.yaml      enabled platforms, specs, iteration/concurrency config
docker-compose.yml         self-hosted comparison DBs, resource-capped
tests/                     unit tests against an in-memory FakeAdapter
docs/                      methodology + analysis write-up template
```

## Setup

### 1. Prerequisites

- Python 3.10+
- Docker + Docker Compose (for the self-hosted comparison platforms)
- Outbound internet access (SNAP dataset download, cloud DB endpoints)

### 2. Set up CognoDB Cloud

Per the assignment brief:

1. Sign up at <https://console.cognodb.com/signup> (free, no credit card).
2. Create a free (c0) instance, pick a region.
3. Save the `bolt+s://<instance-id>.databases.cognodb.cloud` URI and the
   generated password for user `cognodb` — **it is shown once.**
4. Put those into `.env` (see below). Connectivity is via the official
   Neo4j driver, already wired up in `src/benchmark/adapters/cognodb_adapter.py`.

### 3. Set up Neo4j AuraDB Free

Create a free instance at <https://console.neo4j.io>, save its
`neo4j+s://...` URI and password.

### 4. Configure environment

```bash
cp .env.example .env
# then fill in COGNODB_URI / COGNODB_PASSWORD / NEO4J_AURA_URI / NEO4J_AURA_PASSWORD
```

`.env` is git-ignored — credentials never enter the repository.

### 5. Install the harness

```bash
python -m venv .venv && source .venv/bin/activate
make setup          # pip install -e ".[dev]"
```

Or run everything containerized instead — see `docker-compose.yml`
(`benchmark` service, profile `runner`).

## Running the benchmark

```bash
make infra-up        # start Memgraph / ArangoDB / SurrealDB (docker compose)
make dataset         # download+sample SNAP, or synthetic if offline
make bench           # run all 5 platforms through every workload
make report          # build results/REPORT.md from results/*.json
make infra-down      # stop and remove the self-hosted containers
```

Or the equivalent one-shot script: `bash scripts/run_all.sh` (after
`scripts/start_infra.sh`). Full start/stop instructions are also in
`SETUP_AND_USAGE.txt` at the repo root.

Run a subset while iterating:

```bash
benchmark bench run --platform memgraph --platform arangodb
```

## Results

*(Generated by `benchmark report` from `results/*.json` — paste the
contents of `results/REPORT.md` here after a real run, or leave this
section linking to that file.)*

See [`results/REPORT.md`](results/REPORT.md) for the full matrix:
ingest throughput, 1/2/3-hop traversal p50/p95, point + indexed lookup
p50/p95, aggregation p50/p95, mixed-workload QPS at 1/10/40 concurrent
clients, and footprint, for every platform.

## Analysis

See [`docs/ANALYSIS.md`](docs/ANALYSIS.md) — fill in after a real run.

## Caveats

Caveats are collected automatically per-platform in `results/*.json`
(`caveats` field) and surfaced in `results/REPORT.md`. Known structural
caveats independent of any single run:

- Neo4j AuraDB Free's exact vCPU/RAM allocation is not published in fine
  detail by Neo4j; the spec row above should be double-checked against your
  actual instance in the Aura console before treating it as verified parity.
- `footprint()` returns `"not observable"` wherever a platform's client
  protocol doesn't expose stored-data size or memory (common on managed
  free tiers) rather than guessing.
- Network latency to each platform's region is not controlled for — all
  runs should be executed from the same machine/network for internal
  consistency, but absolute cross-platform comparisons still include each
  provider's network path.

## Reproducing from scratch

```bash
git clone <this-repo-url>
cd cognodb-graph-benchmark
cp .env.example .env   # fill in CognoDB + Neo4j Aura credentials
make setup
make infra-up
make dataset
make bench
make report
make infra-down
```

Anyone with free-tier accounts on CognoDB and Neo4j Aura, and Docker
installed, can run this end to end with no code changes.

## Testing

`tests/` covers the orchestration logic (batching, percentile math, mixed-
workload concurrency, failure handling, report generation) against an
in-memory `FakeAdapter`, so it runs in CI without live database credentials:

```bash
make test
```

## License

MIT — see `LICENSE`.