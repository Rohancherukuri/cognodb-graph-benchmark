from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

from .load_epinions import read_epinions_edges
from .synthetic import generate_synthetic


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_RAW_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "soc-Epinions1.txt"
)


def prepare_dataset(
    source: str,
    target_edges: int,
    out_dir: Path,
    seed: int = 42,
    raw_data_path: Path = DEFAULT_RAW_DATA_PATH,
) -> dict:
    """
    Prepare a canonical benchmark dataset.

    The output contains:

    - nodes.csv
    - edges.csv
    - manifest.json

    Supported sources:

    - epinions
    - synthetic
    """

    if target_edges <= 0:
        raise ValueError(
            "target_edges must be greater than zero."
        )

    if source == "epinions":
        return _prepare_epinions(
            raw_data_path=raw_data_path,
            target_edges=target_edges,
            out_dir=out_dir,
            seed=seed,
        )

    if source == "synthetic":
        manifest = generate_synthetic(
            target_edges=target_edges,
            out_dir=out_dir,
            seed=seed,
        )

        _finalize_manifest(
            manifest=manifest,
            out_dir=out_dir,
            target_edges=target_edges,
        )

        return manifest

    raise ValueError(
        f"Unsupported dataset source: {source!r}. "
        "Supported sources are: "
        "'epinions', 'synthetic'."
    )


def _prepare_epinions(
    raw_data_path: Path,
    target_edges: int,
    out_dir: Path,
    seed: int,
) -> dict:
    """
    Create a deterministic subset of the Epinions dataset.
    """

    edges = read_epinions_edges(
        raw_data_path
    )

    if target_edges > len(edges):
        raise ValueError(
            f"Requested {target_edges:,} relationships, "
            f"but the raw dataset contains only "
            f"{len(edges):,}."
        )

    rng = random.Random(seed)

    sampled_edges = rng.sample(
        edges,
        target_edges,
    )

    nodes = sorted(
        {
            node_id
            for source_id, target_id
            in sampled_edges
            for node_id in (
                source_id,
                target_id,
            )
        }
    )

    _validate_dataset(
        nodes=nodes,
        edges=sampled_edges,
        target_edges=target_edges,
    )

    _write_nodes(
        nodes=nodes,
        output_path=out_dir / "nodes.csv",
    )

    _write_edges(
        edges=sampled_edges,
        output_path=out_dir / "edges.csv",
    )

    manifest = {
        "source": "SNAP soc-Epinions1",
        "raw_dataset": str(raw_data_path),
        "raw_relationship_count": len(edges),
        "node_count": len(nodes),
        "relationship_count": len(sampled_edges),
        "relationship_type": "TRUSTS",
        "sampling_method": (
            "deterministic random sampling"
        ),
        "seed": seed,
    }

    _finalize_manifest(
        manifest=manifest,
        out_dir=out_dir,
        target_edges=target_edges,
    )

    return manifest


def _validate_dataset(
    nodes: list[int],
    edges: list[tuple[int, int]],
    target_edges: int,
) -> None:
    """
    Validate the canonical graph dataset.
    """

    if len(edges) != target_edges:
        raise ValueError(
            f"Expected {target_edges:,} relationships "
            f"but found {len(edges):,}."
        )

    if not nodes:
        raise ValueError(
            "Dataset contains no nodes."
        )

    node_set = set(nodes)

    for source_id, target_id in edges:

        if source_id not in node_set:
            raise ValueError(
                f"Missing source node: {source_id}"
            )

        if target_id not in node_set:
            raise ValueError(
                f"Missing target node: {target_id}"
            )


def _write_nodes(
    nodes: list[int],
    output_path: Path,
) -> None:
    """
    Write canonical nodes.csv.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            ["node_id"]
        )

        for node_id in nodes:

            writer.writerow(
                [node_id]
            )


def _write_edges(
    edges: list[tuple[int, int]],
    output_path: Path,
) -> None:
    """
    Write canonical edges.csv.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "source_id",
                "target_id",
                "relationship_type",
            ]
        )

        for source_id, target_id in edges:

            writer.writerow(
                [
                    source_id,
                    target_id,
                    "TRUSTS",
                ]
            )


def _finalize_manifest(
    manifest: dict,
    out_dir: Path,
    target_edges: int,
) -> None:
    """
    Add reproducibility metadata and
    write manifest.json.
    """

    nodes_path = out_dir / "nodes.csv"
    edges_path = out_dir / "edges.csv"

    manifest["nodes_sha256"] = _sha256(
        nodes_path
    )

    manifest["edges_sha256"] = _sha256(
        edges_path
    )

    manifest[
        "target_edges_requested"
    ] = target_edges

    manifest_path = (
        out_dir
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )


def _sha256(
    path: Path,
) -> str:
    """
    Calculate the SHA-256 hash of a file.
    """

    digest = hashlib.sha256()

    with path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(8192),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()

def main() -> None:
    try:
        manifest = prepare_dataset(
            source="epinions",
            target_edges=300_000,
            out_dir=(
                PROJECT_ROOT
                / "data"
                / "processed"
            ),
            seed=42,
        )

        print(
            json.dumps(
                manifest,
                indent=2,
            )
        )

    except Exception as e:
        print(f"Error occurred inside the main function from prepare.py file:- {e}")

if __name__ == "__main__":
    main()