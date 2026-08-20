from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from .config import BenchmarkConfig
from .dataset.prepare import prepare_dataset
from .metrics.report import build_report
from .orchestrator import run_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
CONFIG_PATH = ROOT / "config" / "platforms.yaml"


@click.group()
def cli():
    """CognoDB Cloud graph-database benchmark suite."""


@cli.group()
def dataset():
    """Prepare the benchmark dataset."""


@dataset.command("prepare")
@click.option("--source", type=click.Choice(["snap", "synthetic"]), default="snap", show_default=True)
@click.option("--target-edges", default=300_000, show_default=True)
def dataset_prepare(source: str, target_edges: int):
    """Download (or generate) nodes.csv / edges.csv into data/processed/."""
    manifest = prepare_dataset(source=source, target_edges=target_edges, out_dir=DATA_DIR)
    click.echo(json.dumps(manifest, indent=2))


@cli.group()
def bench():
    """Run the benchmark against one or more platforms."""


@bench.command("run")
@click.option(
    "--platform",
    "platforms",
    multiple=True,
    default=("all",),
    help="Repeatable. Platform name(s) from config/platforms.yaml, or 'all'.",
)
def bench_run(platforms: tuple[str, ...]):
    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)
    if "all" not in platforms:
        cfg.enabled_platforms = [p for p in cfg.enabled_platforms if p in platforms]
    nodes_path, edges_path = DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv"
    if not nodes_path.exists() or not edges_path.exists():
        raise click.ClickException("dataset not found - run `benchmark dataset prepare` first")
    results = run_all(cfg, nodes_path, edges_path, RESULTS_DIR)
    click.echo(f"wrote {len(results)} result file(s) to {RESULTS_DIR}")


@cli.command("report")
def report_cmd():
    """Build results/REPORT.md from the per-platform JSON result files."""
    out = build_report(RESULTS_DIR, RESULTS_DIR / "REPORT.md")
    click.echo(f"report written to {out}")


if __name__ == "__main__":
    cli()
