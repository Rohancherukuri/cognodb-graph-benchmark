from pathlib import Path

import pytest

from benchmark.dataset.load_epinions import read_epinions_edges


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

RAW_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "soc-Epinions1.txt"
)


@pytest.mark.dataset
def test_real_epinions_dataset_statistics() -> None:
    """
    Validate the expected relationship count
    of the real Epinions dataset.
    """

    if not RAW_DATA_PATH.exists():
        pytest.skip(
            "Real Epinions dataset is not available."
        )

    edges = read_epinions_edges(
        RAW_DATA_PATH
    )

    assert len(edges) == 508_837

    nodes = {
        node_id
        for source_id, target_id in edges
        for node_id in (
            source_id,
            target_id,
        )
    }

    assert len(nodes) == 75_879