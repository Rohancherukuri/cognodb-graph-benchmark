from pathlib import Path

import pytest

from benchmark.dataset.load_epinions import read_epinions_edges


def test_read_epinions_edges_from_valid_file(
    tmp_path: Path,
) -> None:
    """
    Verify that comment lines and blank lines are ignored
    and valid relationships are parsed correctly.
    """

    dataset_path = (
        tmp_path
        / "epinions.txt"
    )

    dataset_path.write_text(
        """
# Dataset comment
# Another comment

0 4
0 5
10 20
""".strip(),
        encoding="utf-8",
    )

    edges = read_epinions_edges(
        dataset_path
    )

    assert edges == [
        (0, 4),
        (0, 5),
        (10, 20),
    ]


def test_read_epinions_edges_missing_file(
    tmp_path: Path,
) -> None:
    """
    Verify that a missing dataset raises FileNotFoundError.
    """

    missing_path = (
        tmp_path
        / "missing.txt"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        read_epinions_edges(
            missing_path
        )


def test_read_epinions_edges_invalid_row(
    tmp_path: Path,
) -> None:
    """
    Verify malformed rows raise ValueError.
    """

    dataset_path = (
        tmp_path
        / "invalid.txt"
    )

    dataset_path.write_text(
        """
0 1
1 2 3
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid edge format",
    ):
        read_epinions_edges(
            dataset_path
        )


def test_read_epinions_edges_invalid_node_id(
    tmp_path: Path,
) -> None:
    """
    Verify non-integer node IDs raise ValueError.
    """

    dataset_path = (
        tmp_path
        / "invalid.txt"
    )

    dataset_path.write_text(
        """
0 1
abc 2
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid node ID",
    ):
        read_epinions_edges(
            dataset_path
        )