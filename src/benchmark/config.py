from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SPECS = {
    "cognodb": {"vcpu": 0.5, "ram_mb": 256, "disk_gb": 1, "tier": "CognoDB free (c0)"},
    "neo4j_aura": {"vcpu": 0.5, "ram_mb": 256, "disk_gb": 1, "tier": "Neo4j AuraDB Free"},
    "memgraph": {"vcpu": 0.5, "ram_mb": 256, "disk_gb": 1, "tier": "self-hosted, docker-capped"},
    "arangodb": {"vcpu": 0.5, "ram_mb": 256, "disk_gb": 1, "tier": "self-hosted, docker-capped"},
    "dgraph": {"vcpu": 0.5, "ram_mb": 256, "disk_gb": 1, "tier": "self-hosted, docker-capped"},
}


@dataclass
class BenchmarkConfig:
    """Everything the orchestrator needs for a run. Values come from
    config/platforms.yaml, overridable by environment variables so CI or a
    quick local run can tune iteration counts without editing the file.
    """

    enabled_platforms: list[str]
    iterations: int = 100
    concurrency_levels: list[int] = field(default_factory=lambda: [1, 10, 40])
    mixed_duration_seconds: int = 30
    mixed_read_ratio: float = 0.8
    load_batch_size: int = 1000
    random_seed: int = 42
    platform_specs: dict = field(default_factory=lambda: dict(DEFAULT_SPECS))

    @classmethod
    def from_yaml(cls, path: Path) -> "BenchmarkConfig":
        raw = yaml.safe_load(path.read_text()) if path.exists() else {}
        specs = dict(DEFAULT_SPECS)
        specs.update(raw.get("platform_specs", {}))

        conc_env = os.environ.get("BENCHMARK_CONCURRENCY_LEVELS")
        if conc_env:
            concurrency_levels = [int(x) for x in conc_env.split(",")]
        else:
            concurrency_levels = list(raw.get("concurrency_levels", [1, 10, 40]))

        return cls(
            enabled_platforms=list(raw.get("enabled_platforms", list(DEFAULT_SPECS))),
            iterations=int(os.environ.get("BENCHMARK_ITERATIONS", raw.get("iterations", 100))),
            concurrency_levels=concurrency_levels,
            mixed_duration_seconds=int(
                os.environ.get("BENCHMARK_MIXED_DURATION_SEC", raw.get("mixed_duration_seconds", 30))
            ),
            mixed_read_ratio=float(raw.get("mixed_read_ratio", 0.8)),
            load_batch_size=int(raw.get("load_batch_size", 1000)),
            random_seed=int(os.environ.get("RANDOM_SEED", raw.get("random_seed", 42))),
            platform_specs=specs,
        )
