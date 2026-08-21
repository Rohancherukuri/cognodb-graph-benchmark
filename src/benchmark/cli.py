# from __future__ import annotations

# import json
# import logging
# from pathlib import Path

# import click

# from .config import BenchmarkConfig
# from .dataset.prepare import prepare_dataset
# from .metrics.report import build_report
# from .orchestrator import run_all

# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ROOT = Path(__file__).resolve().parents[2]
# DATA_DIR = ROOT / "data" / "processed"
# RESULTS_DIR = ROOT / "results"
# CONFIG_PATH = ROOT / "config" / "platforms.yaml"


# @click.group()
# def cli():
#     """CognoDB Cloud graph-database benchmark suite."""


# @cli.group()
# def dataset():
#     """Prepare the benchmark dataset."""


# @dataset.command("prepare")
# @click.option("--source", type=click.Choice(["snap", "synthetic"]), default="snap", show_default=True)
# @click.option("--target-edges", default=300_000, show_default=True)
# def dataset_prepare(source: str, target_edges: int):
#     """Download (or generate) nodes.csv / edges.csv into data/processed/."""
#     manifest = prepare_dataset(source=source, target_edges=target_edges, out_dir=DATA_DIR)
#     click.echo(json.dumps(manifest, indent=2))


# @cli.group()
# def bench():
#     """Run the benchmark against one or more platforms."""


# @bench.command("run")
# @click.option(
#     "--platform",
#     "platforms",
#     multiple=True,
#     default=("all",),
#     help="Repeatable. Platform name(s) from config/platforms.yaml, or 'all'.",
# )
# def bench_run(platforms: tuple[str, ...]):
#     cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)
#     if "all" not in platforms:
#         cfg.enabled_platforms = [p for p in cfg.enabled_platforms if p in platforms]
#     nodes_path, edges_path = DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv"
#     if not nodes_path.exists() or not edges_path.exists():
#         raise click.ClickException("dataset not found - run `benchmark dataset prepare` first")
#     results = run_all(cfg, nodes_path, edges_path, RESULTS_DIR)
#     click.echo(f"wrote {len(results)} result file(s) to {RESULTS_DIR}")


# @cli.command("report")
# def report_cmd():
#     """Build results/REPORT.md from the per-platform JSON result files."""
#     out = build_report(RESULTS_DIR, RESULTS_DIR / "REPORT.md")
#     click.echo(f"report written to {out}")


# if __name__ == "__main__":
#     cli()

from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from .config import BenchmarkConfig
from .dataset.prepare import prepare_dataset
from .metrics.report import build_report
from .orchestrator import run_all


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# Repository root
ROOT = Path(__file__).resolve().parents[2]

# Project directories
RAW_DATA_DIR = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"

# Configuration
CONFIG_PATH = ROOT / "config" / "platforms.yaml"


@click.group()
def cli() -> None:
    """CognoDB graph database benchmark suite."""


# ============================================================
# DATASET COMMANDS
# ============================================================

@cli.group()
def dataset() -> None:
    """Prepare benchmark datasets."""


@dataset.command("prepare")
@click.option(
    "--source",
    type=click.Choice(
        [
            "epinions",
            "synthetic",
        ]
    ),
    default="epinions",
    show_default=True,
    help="Dataset source to prepare.",
)
@click.option(
    "--target-edges",
    type=int,
    default=100_000,
    show_default=True,
    help="Maximum number of relationships to include.",
)
def dataset_prepare(
    source: str,
    target_edges: int,
) -> None:
    """
    Prepare the benchmark dataset.

    Creates:

        data/processed/nodes.csv
        data/processed/edges.csv
        data/processed/manifest.json
    """

    try:
        manifest = prepare_dataset(
            source=source,
            target_edges=target_edges,
            out_dir=DATA_DIR,
        )

    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        "\nDataset prepared successfully.\n"
    )

    click.echo(
        json.dumps(
            manifest,
            indent=2,
        )
    )


# ============================================================
# BENCHMARK COMMANDS
# ============================================================

@cli.group()
def bench() -> None:
    """Run benchmarks against graph database platforms."""


@bench.command("run")
@click.option(
    "--platform",
    "platforms",
    multiple=True,
    default=("all",),
    help=(
        "Repeatable platform name(s) from "
        "config/platforms.yaml, or 'all'."
    ),
)
def bench_run(
    platforms: tuple[str, ...],
) -> None:
    """Run the benchmark workload."""

    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)

    if "all" not in platforms:
        cfg.enabled_platforms = [
            platform
            for platform in cfg.enabled_platforms
            if platform in platforms
        ]

    nodes_path = DATA_DIR / "nodes.csv"
    edges_path = DATA_DIR / "edges.csv"

    if not nodes_path.exists():
        raise click.ClickException(
            f"Nodes dataset not found: {nodes_path}. "
            "Run `benchmark dataset prepare` first."
        )

    if not edges_path.exists():
        raise click.ClickException(
            f"Edges dataset not found: {edges_path}. "
            "Run `benchmark dataset prepare` first."
        )

    click.echo("\nStarting benchmark...\n")

    click.echo(
        f"Platforms: {', '.join(cfg.enabled_platforms)}"
    )

    click.echo(
        f"Nodes: {nodes_path}"
    )

    click.echo(
        f"Edges: {edges_path}\n"
    )

    results = run_all(
        cfg,
        nodes_path,
        edges_path,
        RESULTS_DIR,
    )

    click.echo(
        f"\nBenchmark complete."
    )

    click.echo(
        f"Wrote {len(results)} result file(s) "
        f"to {RESULTS_DIR}"
    )


# ============================================================
# REPORT COMMANDS
# ============================================================

@cli.command("report")
def report_cmd() -> None:
    """Build a benchmark report from platform result files."""

    report_path = RESULTS_DIR / "REPORT.md"

    out = build_report(
        RESULTS_DIR,
        report_path,
    )

    click.echo(
        f"Report written to {out}"
    )

def main() -> None:
    """Entry point for the benchmark CLI."""
    cli()

if __name__ == "__main__":
    main()