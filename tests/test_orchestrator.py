import csv
from pathlib import Path

from benchmark.adapters import registry
from benchmark.config import BenchmarkConfig
from benchmark.orchestrator import run_platform

from .fake_adapter import FakeAdapter


def _write_csv_dataset(tmp_path: Path):
    nodes_path = tmp_path / "nodes.csv"
    edges_path = tmp_path / "edges.csv"
    with open(nodes_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "handle"])
        for i in range(20):
            w.writerow([str(i), f"user{i}"])
    with open(edges_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for i in range(19):
            w.writerow([str(i), str(i + 1)])
    return nodes_path, edges_path


def test_run_platform_with_fake_adapter(tmp_path, monkeypatch):
    monkeypatch.setitem(registry.ADAPTER_REGISTRY, "fake", FakeAdapter)
    nodes_path, edges_path = _write_csv_dataset(tmp_path)
    cfg = BenchmarkConfig(
        enabled_platforms=["fake"],
        iterations=5,
        concurrency_levels=[1, 2],
        mixed_duration_seconds=1,
    )

    result = run_platform("fake", cfg, nodes_path, edges_path)

    assert result.platform == "fake"
    assert not result.caveats
    assert result.ingest["nodes_loaded"] == 20
    assert result.ingest["rels_loaded"] == 19
    assert set(result.traversal.keys()) == {"1hop", "2hop", "3hop"}
    assert result.point_lookup["count"] == 5
    assert len(result.mixed) == 2
    for m in result.mixed:
        assert m["total_ops"] > 0
    assert result.footprint["node_count"] == 20


def test_run_platform_records_caveat_on_failure(tmp_path, monkeypatch):
    class BrokenAdapter(FakeAdapter):
        def connect(self):
            raise RuntimeError("simulated connection failure")

    monkeypatch.setitem(registry.ADAPTER_REGISTRY, "broken", BrokenAdapter)
    nodes_path, edges_path = _write_csv_dataset(tmp_path)
    cfg = BenchmarkConfig(enabled_platforms=["broken"], iterations=5)

    result = run_platform("broken", cfg, nodes_path, edges_path)

    assert result.platform == "broken"
    assert result.caveats  # failure recorded, not raised
