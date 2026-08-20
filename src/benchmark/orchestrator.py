from __future__ import annotations

import csv
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .adapters.base import EdgeRecord, GraphDBAdapter, NodeRecord
from .adapters.registry import ADAPTER_REGISTRY
from .config import BenchmarkConfig
from .metrics.models import IngestResult, MixedResult, PlatformResult
from .metrics.stats import summarize

logger = logging.getLogger("benchmark.orchestrator")


def _read_csv_nodes(path: Path):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            yield NodeRecord(node_id=row["id"], label="Person", props={"handle": row.get("handle", row["id"])})


def _read_csv_edges(path: Path):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            yield EdgeRecord(src_id=row["src"], dst_id=row["dst"], rel_type="FOLLOWS")


def run_platform(
    platform_name: str, cfg: BenchmarkConfig, nodes_path: Path, edges_path: Path
) -> PlatformResult:
    """Runs the full workload sequence (load -> warm-up -> traversal ->
    lookups -> aggregation -> mixed -> footprint) against one platform.
    Failures are caught and recorded as caveats rather than aborting the
    whole suite, so one bad platform doesn't block results for the rest -
    per assignment section 5.3, "record every caveat honestly ... failed
    runs".
    """
    adapter_cls = ADAPTER_REGISTRY[platform_name]
    adapter: GraphDBAdapter = adapter_cls()
    result = PlatformResult(platform=platform_name, specs=cfg.platform_specs.get(platform_name, {}))

    try:
        adapter.connect()
        adapter.clear()
        adapter.create_indexes()
        result.indexed_property = getattr(adapter, "indexed_property", None)

        # ---- ingest ----
        t0 = time.perf_counter()
        n_loaded = adapter.load_nodes(_read_csv_nodes(nodes_path), cfg.load_batch_size)
        r_loaded = adapter.load_edges(_read_csv_edges(edges_path), cfg.load_batch_size)
        wall = time.perf_counter() - t0
        result.ingest = IngestResult(
            nodes_loaded=n_loaded,
            rels_loaded=r_loaded,
            wall_clock_seconds=wall,
            nodes_per_second=(n_loaded / wall) if wall else 0.0,
            rels_per_second=(r_loaded / wall) if wall else 0.0,
        ).__dict__

        # ---- sample start nodes for read workloads ----
        with open(nodes_path, newline="") as f:
            all_ids = [row["id"] for row in csv.DictReader(f)]
        rng = random.Random(cfg.random_seed)
        sample_size = min(cfg.iterations, len(all_ids))
        sample_ids = rng.sample(all_ids, sample_size)

        # ---- warm-up (excluded from reported numbers) ----
        for nid in sample_ids[: max(5, sample_size // 10)]:
            adapter.point_lookup(nid)

        # ---- traversals: 1, 2, 3 hops ----
        for hops in (1, 2, 3):
            latencies = [adapter.traversal(nid, hops) for nid in sample_ids]
            result.traversal[f"{hops}hop"] = summarize(latencies).__dict__

        # ---- lookups ----
        result.point_lookup = summarize([adapter.point_lookup(nid) for nid in sample_ids]).__dict__
        result.indexed_lookup = summarize([adapter.indexed_lookup(nid) for nid in sample_ids]).__dict__

        # ---- aggregation ----
        result.aggregation = summarize([adapter.aggregation() for _ in range(sample_size)]).__dict__

        # ---- mixed read/write workload, swept across concurrency levels ----
        for concurrency in cfg.concurrency_levels:
            stop_at = time.perf_counter() + cfg.mixed_duration_seconds

            def worker() -> int:
                local_ops = 0
                while time.perf_counter() < stop_at:
                    is_read = random.random() < cfg.mixed_read_ratio
                    adapter.mixed_op(is_read)
                    local_ops += 1
                return local_ops

            with ThreadPoolExecutor(max_workers=concurrency) as ex:
                futures = [ex.submit(worker) for _ in range(concurrency)]
                total_ops = sum(f.result() for f in futures)

            result.mixed.append(
                MixedResult(
                    concurrency=concurrency,
                    duration_seconds=cfg.mixed_duration_seconds,
                    read_write_ratio=f"{int(cfg.mixed_read_ratio * 100)}/{int((1 - cfg.mixed_read_ratio) * 100)}",
                    total_ops=total_ops,
                    qps=total_ops / cfg.mixed_duration_seconds,
                ).__dict__
            )

        # ---- footprint ----
        result.footprint = adapter.footprint()

    except Exception as exc:  # noqa: BLE001 - deliberately broad: one platform's
        # failure must not take down the rest of the suite.
        logger.exception("platform %s failed", platform_name)
        result.caveats.append(f"run failed: {exc!r}")
    finally:
        try:
            adapter.close()
        except Exception:
            pass

    return result


def run_all(cfg: BenchmarkConfig, nodes_path: Path, edges_path: Path, out_dir: Path) -> list[PlatformResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for platform in cfg.enabled_platforms:
        logger.info("=== benchmarking %s ===", platform)
        res = run_platform(platform, cfg, nodes_path, edges_path)
        results.append(res)
        (out_dir / f"{platform}.json").write_text(json.dumps(res.to_dict(), indent=2))
    return results
