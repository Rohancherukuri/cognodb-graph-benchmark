from __future__ import annotations

import csv
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator

from .adapters.base import EdgeRecord, GraphDBAdapter, NodeRecord
from .adapters.registry import ADAPTER_REGISTRY
from .config import BenchmarkConfig
from .metrics.models import IngestResult, MixedResult, PlatformResult
from .metrics.stats import summarize


logger = logging.getLogger("benchmark.orchestrator")


# ---------------------------------------------------------------------------
# CSV schema helpers
# ---------------------------------------------------------------------------

NODE_ID_COLUMNS = ("id", "node_id", "node", "vertex_id")

EDGE_SOURCE_COLUMNS = (
    "src",
    "source",
    "source_id",
    "from",
    "from_id",
)

EDGE_TARGET_COLUMNS = (
    "dst",
    "target",
    "target_id",
    "to",
    "to_id",
)


def _get_first_value(
    row: dict[str, str],
    columns: tuple[str, ...],
    *,
    path: Path,
    record_type: str,
) -> str:
    """
    Return the first non-empty value found from the supported column names.

    Raises a helpful error instead of a generic KeyError when the processed
    dataset schema does not match the benchmark's expectations.
    """
    for column in columns:
        value = row.get(column)

        if value is not None and value != "":
            return str(value)

    available_columns = ", ".join(row.keys())

    raise ValueError(
        f"Could not determine {record_type} from CSV file: {path}. "
        f"Expected one of: {', '.join(columns)}. "
        f"Available columns: {available_columns}"
    )


# ---------------------------------------------------------------------------
# Dataset readers
# ---------------------------------------------------------------------------

def _read_csv_nodes(path: Path) -> Iterator[NodeRecord]:
    """
    Stream nodes from the processed CSV.

    Supported node identifier columns:

        id
        node_id
        node
        vertex_id

    The benchmark internally standardizes every node as a NodeRecord.
    """

    with path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"Node CSV file has no header: {path}"
            )

        for row in reader:
            node_id = _get_first_value(
                row,
                NODE_ID_COLUMNS,
                path=path,
                record_type="node identifier",
            )

            handle = (
                row.get("handle")
                or row.get("username")
                or row.get("name")
                or node_id
            )

            yield NodeRecord(
                node_id=node_id,
                label="Person",
                props={
                    "handle": str(handle),
                },
            )


def _read_csv_edges(path: Path) -> Iterator[EdgeRecord]:
    """
    Stream edges from the processed CSV.

    Supported source columns:

        src
        source
        source_id
        from
        from_id

    Supported destination columns:

        dst
        target
        target_id
        to
        to_id

    Relationship type is read from the CSV when available. Otherwise the
    Epinions dataset relationship type defaults to TRUSTS.
    """

    with path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"Edge CSV file has no header: {path}"
            )

        for row in reader:
            src_id = _get_first_value(
                row,
                EDGE_SOURCE_COLUMNS,
                path=path,
                record_type="edge source identifier",
            )

            dst_id = _get_first_value(
                row,
                EDGE_TARGET_COLUMNS,
                path=path,
                record_type="edge destination identifier",
            )

            rel_type = (
                row.get("rel_type")
                or row.get("relationship_type")
                or row.get("type")
                or "TRUSTS"
            )

            yield EdgeRecord(
                src_id=src_id,
                dst_id=dst_id,
                rel_type=str(rel_type),
            )


def _read_node_ids(path: Path) -> list[str]:
    """
    Read node IDs using exactly the same schema logic as _read_csv_nodes().

    This prevents ingestion from succeeding while workload sampling later
    fails with a KeyError because the CSV does not contain an 'id' column.
    """

    node_ids: list[str] = []

    with path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"Node CSV file has no header: {path}"
            )

        for row in reader:
            node_id = _get_first_value(
                row,
                NODE_ID_COLUMNS,
                path=path,
                record_type="node identifier",
            )

            node_ids.append(node_id)

    if not node_ids:
        raise ValueError(
            f"No node IDs found in dataset: {path}"
        )

    return node_ids


# ---------------------------------------------------------------------------
# Platform benchmark
# ---------------------------------------------------------------------------

def run_platform(
    platform_name: str,
    cfg: BenchmarkConfig,
    nodes_path: Path,
    edges_path: Path,
) -> PlatformResult:
    """
    Run the complete benchmark workload against one graph database platform.

    Workflow:

        1. Connect
        2. Clear previous benchmark data
        3. Create indexes
        4. Load nodes
        5. Load relationships
        6. Sample nodes
        7. Warm-up
        8. Traversal benchmarks
        9. Point lookup benchmarks
        10. Indexed lookup benchmarks
        11. Aggregation benchmarks
        12. Mixed read/write workload
        13. Footprint collection

    Failures are captured as caveats so that one failed platform does not
    prevent the remaining databases from completing their benchmarks.
    """

    adapter_cls = ADAPTER_REGISTRY[platform_name]
    adapter: GraphDBAdapter = adapter_cls()

    result = PlatformResult(
        platform=platform_name,
        specs=cfg.platform_specs.get(platform_name, {}),
    )

    try:
        # -------------------------------------------------------------------
        # Connect and prepare database
        # -------------------------------------------------------------------

        logger.info(
            "[%s] connecting",
            platform_name,
        )

        adapter.connect()

        logger.info(
            "[%s] clearing benchmark data",
            platform_name,
        )

        adapter.clear()

        logger.info(
            "[%s] creating indexes",
            platform_name,
        )

        adapter.create_indexes()

        result.indexed_property = getattr(
            adapter,
            "indexed_property",
            None,
        )

        # -------------------------------------------------------------------
        # Ingest
        # -------------------------------------------------------------------

        logger.info(
            "[%s] loading nodes",
            platform_name,
        )

        ingest_start = time.perf_counter()

        n_loaded = adapter.load_nodes(
            _read_csv_nodes(nodes_path),
            cfg.load_batch_size,
        )

        logger.info(
            "[%s] loaded %s nodes",
            platform_name,
            n_loaded,
        )

        logger.info(
            "[%s] loading relationships",
            platform_name,
        )

        r_loaded = adapter.load_edges(
            _read_csv_edges(edges_path),
            cfg.load_batch_size,
        )

        logger.info(
            "[%s] loaded %s relationships",
            platform_name,
            r_loaded,
        )

        ingest_wall = time.perf_counter() - ingest_start

        result.ingest = IngestResult(
            nodes_loaded=n_loaded,
            rels_loaded=r_loaded,
            wall_clock_seconds=ingest_wall,
            nodes_per_second=(
                n_loaded / ingest_wall
                if ingest_wall > 0
                else 0.0
            ),
            rels_per_second=(
                r_loaded / ingest_wall
                if ingest_wall > 0
                else 0.0
            ),
        ).__dict__

        # -------------------------------------------------------------------
        # Sample nodes for read workloads
        # -------------------------------------------------------------------

        logger.info(
            "[%s] reading workload sample",
            platform_name,
        )

        all_ids = _read_node_ids(nodes_path)

        rng = random.Random(cfg.random_seed)

        sample_size = min(
            cfg.iterations,
            len(all_ids),
        )

        if sample_size == 0:
            raise ValueError(
                "Cannot run read workloads because the dataset contains "
                "zero nodes."
            )

        sample_ids = rng.sample(
            all_ids,
            sample_size,
        )

        logger.info(
            "[%s] selected %s workload nodes",
            platform_name,
            sample_size,
        )

        # -------------------------------------------------------------------
        # Warm-up
        # -------------------------------------------------------------------

        warmup_count = min(
            sample_size,
            max(5, sample_size // 10),
        )

        logger.info(
            "[%s] warm-up with %s lookups",
            platform_name,
            warmup_count,
        )

        for node_id in sample_ids[:warmup_count]:
            adapter.point_lookup(node_id)

        # -------------------------------------------------------------------
        # Traversal benchmarks
        # -------------------------------------------------------------------

        for hops in (1, 2, 3):
            logger.info(
                "[%s] running %s-hop traversal benchmark",
                platform_name,
                hops,
            )

            latencies = [
                adapter.traversal(
                    node_id,
                    hops,
                )
                for node_id in sample_ids
            ]

            result.traversal[f"{hops}hop"] = (
                summarize(latencies).__dict__
            )

        # -------------------------------------------------------------------
        # Point lookup
        # -------------------------------------------------------------------

        logger.info(
            "[%s] running point lookup benchmark",
            platform_name,
        )

        point_lookup_latencies = [
            adapter.point_lookup(node_id)
            for node_id in sample_ids
        ]

        result.point_lookup = (
            summarize(point_lookup_latencies).__dict__
        )

        # -------------------------------------------------------------------
        # Indexed lookup
        # -------------------------------------------------------------------

        logger.info(
            "[%s] running indexed lookup benchmark",
            platform_name,
        )

        indexed_lookup_latencies = [
            adapter.indexed_lookup(node_id)
            for node_id in sample_ids
        ]

        result.indexed_lookup = (
            summarize(indexed_lookup_latencies).__dict__
        )

        # -------------------------------------------------------------------
        # Aggregation
        # -------------------------------------------------------------------

        logger.info(
            "[%s] running aggregation benchmark",
            platform_name,
        )

        aggregation_latencies = [
            adapter.aggregation()
            for _ in range(sample_size)
        ]

        result.aggregation = (
            summarize(aggregation_latencies).__dict__
        )

        # -------------------------------------------------------------------
        # Mixed read/write workload
        # -------------------------------------------------------------------

        for concurrency in cfg.concurrency_levels:
            logger.info(
                "[%s] running mixed workload with concurrency=%s",
                platform_name,
                concurrency,
            )

            stop_at = (
                time.perf_counter()
                + cfg.mixed_duration_seconds
            )

            def worker() -> int:
                local_ops = 0

                while time.perf_counter() < stop_at:
                    is_read = (
                        random.random()
                        < cfg.mixed_read_ratio
                    )

                    adapter.mixed_op(is_read)

                    local_ops += 1

                return local_ops

            with ThreadPoolExecutor(
                max_workers=concurrency,
            ) as executor:
                futures = [
                    executor.submit(worker)
                    for _ in range(concurrency)
                ]

                total_ops = sum(
                    future.result()
                    for future in futures
                )

            result.mixed.append(
                MixedResult(
                    concurrency=concurrency,
                    duration_seconds=cfg.mixed_duration_seconds,
                    read_write_ratio=(
                        f"{int(cfg.mixed_read_ratio * 100)}/"
                        f"{int((1 - cfg.mixed_read_ratio) * 100)}"
                    ),
                    total_ops=total_ops,
                    qps=(
                        total_ops
                        / cfg.mixed_duration_seconds
                    ),
                ).__dict__
            )

        # -------------------------------------------------------------------
        # Footprint
        # -------------------------------------------------------------------

        logger.info(
            "[%s] collecting footprint",
            platform_name,
        )

        result.footprint = adapter.footprint()

        logger.info(
            "[%s] benchmark completed successfully",
            platform_name,
        )

    except Exception as exc:
        # One platform failing must not stop the entire benchmark suite.
        logger.exception(
            "platform %s failed",
            platform_name,
        )

        result.caveats.append(
            f"run failed: {exc!r}"
        )

    finally:
        try:
            adapter.close()

        except Exception:
            logger.exception(
                "failed to close adapter for %s",
                platform_name,
            )

    return result


# ---------------------------------------------------------------------------
# Run all enabled platforms
# ---------------------------------------------------------------------------

def run_all(
    cfg: BenchmarkConfig,
    nodes_path: Path,
    edges_path: Path,
    out_dir: Path,
) -> list[PlatformResult]:
    """
    Run the benchmark against every enabled platform and write one JSON
    result file per platform.
    """

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    results: list[PlatformResult] = []

    for platform_name in cfg.enabled_platforms:
        logger.info(
            "=== benchmarking %s ===",
            platform_name,
        )

        result = run_platform(
            platform_name,
            cfg,
            nodes_path,
            edges_path,
        )

        results.append(result)

        output_path = (
            out_dir
            / f"{platform_name}.json"
        )

        output_path.write_text(
            json.dumps(
                result.to_dict(),
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info(
            "[%s] wrote result to %s",
            platform_name,
            output_path,
        )

    return results