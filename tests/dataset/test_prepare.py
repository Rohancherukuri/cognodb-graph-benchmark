import csv
import hashlib
import json
from pathlib import Path

import pytest

from benchmark.dataset.prepare import prepare_dataset


@pytest.fixture
def raw_epinions_file(
    tmp_path: Path,
) -> Path:
    """
    Create a small Epinions-format dataset
    for deterministic tests.
    """

    raw_path = (
        tmp_path
        / "soc-Epinions1.txt"
    )

    raw_path.write_text(
        """
# Directed Epinions social network
# Nodes: 10 Edges: 10
0 1
0 2
1 2
1 3
2 3
2 4
3 4
3 5
4 5
4 6
""".strip(),
        encoding="utf-8",
    )

    return raw_path


def test_prepare_epinions_dataset(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    Verify that dataset preparation generates
    the expected files and relationship count.
    """

    output_dir = (
        tmp_path
        / "processed"
    )

    manifest = prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_dir,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    assert manifest[
        "relationship_count"
    ] == 5

    assert (
        output_dir
        / "nodes.csv"
    ).exists()

    assert (
        output_dir
        / "edges.csv"
    ).exists()

    assert (
        output_dir
        / "manifest.json"
    ).exists()


def test_prepare_epinions_is_deterministic(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    The same source and seed should produce
    identical output.
    """

    output_one = (
        tmp_path
        / "output_one"
    )

    output_two = (
        tmp_path
        / "output_two"
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_one,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_two,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    assert (
        output_one
        / "edges.csv"
    ).read_bytes() == (
        output_two
        / "edges.csv"
    ).read_bytes()

    assert (
        output_one
        / "nodes.csv"
    ).read_bytes() == (
        output_two
        / "nodes.csv"
    ).read_bytes()


def test_prepare_epinions_changes_with_seed(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    Different seeds should normally produce
    different samples.
    """

    output_one = (
        tmp_path
        / "output_one"
    )

    output_two = (
        tmp_path
        / "output_two"
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_one,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_two,
        seed=99,
        raw_data_path=raw_epinions_file,
    )

    assert (
        output_one
        / "edges.csv"
    ).read_bytes() != (
        output_two
        / "edges.csv"
    ).read_bytes()


def test_prepare_epinions_rejects_too_many_edges(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    Requesting more relationships than exist
    should fail.
    """

    with pytest.raises(
        ValueError,
        match="raw dataset contains only",
    ):
        prepare_dataset(
            source="epinions",
            target_edges=100,
            out_dir=tmp_path / "output",
            raw_data_path=raw_epinions_file,
        )


def test_processed_edges_reference_valid_nodes(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    Every source and target node in edges.csv
    must exist in nodes.csv.
    """

    output_dir = (
        tmp_path
        / "processed"
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_dir,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    with (
        output_dir
        / "nodes.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        nodes = {
            int(row["node_id"])
            for row in reader
        }

    with (
        output_dir
        / "edges.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            assert (
                int(
                    row["source_id"]
                )
                in nodes
            )

            assert (
                int(
                    row["target_id"]
                )
                in nodes
            )


def test_manifest_hashes_match_files(
    raw_epinions_file: Path,
    tmp_path: Path,
) -> None:
    """
    Verify manifest SHA-256 values match
    the generated CSV files.
    """

    output_dir = (
        tmp_path
        / "processed"
    )

    prepare_dataset(
        source="epinions",
        target_edges=5,
        out_dir=output_dir,
        seed=42,
        raw_data_path=raw_epinions_file,
    )

    manifest_path = (
        output_dir
        / "manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )

    nodes_hash = hashlib.sha256(
        (
            output_dir
            / "nodes.csv"
        ).read_bytes()
    ).hexdigest()

    edges_hash = hashlib.sha256(
        (
            output_dir
            / "edges.csv"
        ).read_bytes()
    ).hexdigest()

    assert (
        manifest["nodes_sha256"]
        == nodes_hash
    )

    assert (
        manifest["edges_sha256"]
        == edges_hash
    )