import json
from pathlib import Path

from benchmark.metrics.report import build_report


def test_build_report_handles_missing_fields(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "fake.json").write_text(json.dumps({
        "platform": "fake",
        "specs": {"tier": "test", "vcpu": 0.5, "ram_mb": 256, "disk_gb": 1},
        "ingest": {"nodes_per_second": 100.0, "rels_per_second": 200.0, "wall_clock_seconds": 5.0},
        "traversal": {"1hop": {"p50_ms": 1.0, "p95_ms": 2.0}},
        "point_lookup": {"p50_ms": 0.5, "p95_ms": 0.8},
        "indexed_lookup": {"p50_ms": 0.6, "p95_ms": 0.9},
        "indexed_property": "handle",
        "aggregation": {"p50_ms": 3.0, "p95_ms": 4.0},
        "mixed": [{"concurrency": 1, "qps": 500.0}],
        "footprint": {"node_count": 10},
        "caveats": [],
    }))

    out = build_report(results_dir, tmp_path / "REPORT.md")

    text = out.read_text()
    assert "fake" in text
    assert "Ingest throughput" in text
    assert "Traversal - 1hop" in text
    assert "none recorded" in text
