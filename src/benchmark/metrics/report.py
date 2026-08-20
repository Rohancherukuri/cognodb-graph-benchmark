from __future__ import annotations

import json
from pathlib import Path

from tabulate import tabulate


def build_report(results_dir: Path, out_path: Path) -> Path:
    files = sorted(results_dir.glob("*.json"))
    platforms = [json.loads(f.read_text()) for f in files]
    lines = ["# Benchmark results", ""]

    lines += ["## Platform specs", ""]
    rows = [
        [p["platform"], p.get("specs", {}).get("tier", "n/a"),
         p.get("specs", {}).get("vcpu", "n/a"), p.get("specs", {}).get("ram_mb", "n/a"),
         p.get("specs", {}).get("disk_gb", "n/a")]
        for p in platforms
    ]
    lines.append(tabulate(rows, headers=["platform", "tier", "vCPU", "RAM (MB)", "disk (GB)"], tablefmt="github"))
    lines.append("")

    lines += ["## Ingest throughput", ""]
    rows = [
        [p["platform"],
         _fmt(p.get("ingest", {}), "nodes_per_second"),
         _fmt(p.get("ingest", {}), "rels_per_second"),
         _fmt(p.get("ingest", {}), "wall_clock_seconds")]
        for p in platforms
    ]
    lines.append(tabulate(rows, headers=["platform", "nodes/s", "rels/s", "wall clock (s)"], tablefmt="github"))
    lines.append("")

    for hop in ("1hop", "2hop", "3hop"):
        lines += [f"## Traversal - {hop}", ""]
        rows = [
            [p["platform"], _fmt(p.get("traversal", {}).get(hop, {}), "p50_ms"),
             _fmt(p.get("traversal", {}).get(hop, {}), "p95_ms")]
            for p in platforms
        ]
        lines.append(tabulate(rows, headers=["platform", "p50 (ms)", "p95 (ms)"], tablefmt="github"))
        lines.append("")

    lines += ["## Lookups", ""]
    rows = [
        [p["platform"],
         _fmt(p.get("point_lookup") or {}, "p50_ms"), _fmt(p.get("point_lookup") or {}, "p95_ms"),
         _fmt(p.get("indexed_lookup") or {}, "p50_ms"), _fmt(p.get("indexed_lookup") or {}, "p95_ms"),
         p.get("indexed_property", "n/a")]
        for p in platforms
    ]
    lines.append(tabulate(
        rows,
        headers=["platform", "point p50", "point p95", "indexed p50", "indexed p95", "indexed property"],
        tablefmt="github",
    ))
    lines.append("")

    lines += ["## Aggregation", ""]
    rows = [
        [p["platform"], _fmt(p.get("aggregation") or {}, "p50_ms"), _fmt(p.get("aggregation") or {}, "p95_ms")]
        for p in platforms
    ]
    lines.append(tabulate(rows, headers=["platform", "p50 (ms)", "p95 (ms)"], tablefmt="github"))
    lines.append("")

    lines += ["## Mixed workload - queries/second by concurrency", ""]
    conc_levels = sorted({m["concurrency"] for p in platforms for m in p.get("mixed", [])})
    rows = []
    for p in platforms:
        by_conc = {m["concurrency"]: m["qps"] for m in p.get("mixed", [])}
        rows.append([p["platform"]] + [round(by_conc.get(c, 0), 1) if c in by_conc else "n/a" for c in conc_levels])
    lines.append(tabulate(rows, headers=["platform"] + [f"{c} clients" for c in conc_levels], tablefmt="github"))
    lines.append("")

    lines += ["## Footprint", ""]
    for p in platforms:
        lines.append(f"- **{p['platform']}**: `{json.dumps(p.get('footprint', {}))}`")
    lines.append("")

    lines += ["## Caveats", ""]
    any_caveats = False
    for p in platforms:
        for c in p.get("caveats", []):
            any_caveats = True
            lines.append(f"- **{p['platform']}**: {c}")
    if not any_caveats:
        lines.append("- none recorded")

    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def _fmt(d: dict, key: str) -> str:
    val = d.get(key)
    if val is None:
        return "n/a"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)
