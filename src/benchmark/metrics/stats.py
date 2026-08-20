from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass
class LatencyStats:
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float


def summarize(latencies_ms: list[float]) -> LatencyStats:
    """Percentiles over a list of per-call latencies in milliseconds.
    Uses linear interpolation between closest ranks (same convention as
    numpy.percentile's default), so results are stable and reproducible
    without pulling in numpy just for this.
    """
    if not latencies_ms:
        return LatencyStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    s = sorted(latencies_ms)
    return LatencyStats(
        count=len(s),
        p50_ms=_percentile(s, 50),
        p95_ms=_percentile(s, 95),
        p99_ms=_percentile(s, 99),
        mean_ms=statistics.fmean(s),
        min_ms=s[0],
        max_ms=s[-1],
    )


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)
