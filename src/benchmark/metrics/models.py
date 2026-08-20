from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class IngestResult:
    nodes_loaded: int
    rels_loaded: int
    wall_clock_seconds: float
    nodes_per_second: float
    rels_per_second: float


@dataclass
class MixedResult:
    concurrency: int
    duration_seconds: float
    read_write_ratio: str
    total_ops: int
    qps: float


@dataclass
class PlatformResult:
    platform: str
    specs: dict = field(default_factory=dict)
    ingest: Optional[IngestResult] = None
    traversal: dict = field(default_factory=dict)  # {"1hop": {...LatencyStats...}, ...}
    point_lookup: Optional[dict] = None
    indexed_lookup: Optional[dict] = None
    indexed_property: Optional[str] = None
    aggregation: Optional[dict] = None
    mixed: list = field(default_factory=list)  # list of MixedResult dicts
    footprint: dict = field(default_factory=dict)
    caveats: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class QueryResult:
    """
    Result returned from a graph database query.
    """

    records: list[dict[str, Any]]
    elapsed_seconds: float

@dataclass(frozen=True)
class LoadResult:
    """
    Result returned after loading data.
    """

    nodes_loaded: int
    relationships_loaded: int
    elapsed_seconds: float


@dataclass(frozen=True)
class DatabaseInfo:
    """
    Basic information about a database connection.
    """

    database_name: str
    version: str | None = None
