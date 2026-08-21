from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.config import BenchmarkConfig
from benchmark.orchestrator import run_platform

from ..conftest import requires_env

pytestmark = [pytest.mark.live, requires_env("SURREALDB_URL")]


def test_run_platform_against_real_surrealdb(small_dataset: tuple[Path, Path]) -> None:
    """End-to-end smoke test: load a tiny fixture graph into a real
    SurrealDB instance, run every workload once through the same
    orchestrator code path used for a full benchmark run, and assert the
    result comes back with no caveats.

    This is what actually proves the adapter works against a live
    database - the FakeAdapter-based orchestrator unit tests
    (tests/unit/test_orchestrator.py) only prove the *orchestration logic*
    is correct, never that SurrealQL itself is right.
    """
    nodes_path, edges_path = small_dataset
    cfg = BenchmarkConfig(
        enabled_platforms=["surrealdb"],
        iterations=5,
        concurrency_levels=[1],
        mixed_duration_seconds=2,
    )

    result = run_platform("surrealdb", cfg, nodes_path, edges_path)

    assert result.caveats == [], f"live run recorded caveats: {result.caveats}"
    assert result.ingest is not None
    assert result.ingest["nodes_loaded"] == 10
    assert result.ingest["rels_loaded"] == 9
    assert result.indexed_property == "handle"
    assert set(result.traversal.keys()) == {"1hop", "2hop", "3hop"}
    assert result.footprint.get("node_count") == 10
    assert result.footprint.get("rel_count") == 9