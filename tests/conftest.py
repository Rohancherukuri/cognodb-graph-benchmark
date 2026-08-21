# import os
# import pytest
# from dotenv import load_dotenv
# from neo4j import GraphDatabase

# load_dotenv()

# @pytest.fixture(scope="session")
# def cognodb_driver():
#     """
#     Shared Neo4j-compatible driver connected to
#     CognoDB Cloud.
#     """

#     uri = os.environ.get("COGNODB_URI")
#     user = os.environ.get("COGNODB_USER")
#     password = os.environ.get("COGNODB_PASSWORD")

#     if not uri:
#         pytest.skip(
#             "COGNODB_URI is not configured."
#         )

#     if not user:
#         pytest.skip(
#             "COGNODB_USER is not configured."
#         )

#     if not password:
#         pytest.skip(
#             "COGNODB_PASSWORD is not configured."
#         )

#     driver = GraphDatabase.driver(
#         uri,
#         auth=(user, password),
#     )

#     try:
#         yield driver

#     finally:
#         driver.close()

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterator

import pytest

from benchmark.adapters.base import EdgeRecord, NodeRecord


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live: hits a real, network-reachable graph database (needs credentials)"
    )
    config.addinivalue_line(
        "markers", "network: needs outbound internet access (e.g. downloading a public dataset)"
    )


def requires_env(*names: str) -> "pytest.MarkDecorator":
    """Skip a test unless every named environment variable is set and
    non-empty. Used to gate live-credential tests (SurrealDB, CognoDB, ...)
    so the default `pytest` / `make test` run never needs a real database.

        @pytest.mark.live
        @requires_env("SURREALDB_URL", "SURREALDB_PASSWORD")
        def test_something_live(): ...
    """
    missing = [n for n in names if not os.environ.get(n)]
    return pytest.mark.skipif(
        bool(missing),
        reason=f"missing required env var(s) for a live test: {', '.join(missing)}",
    )


@pytest.fixture
def small_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """Writes a tiny, deterministic nodes.csv/edges.csv pair - a 10-node
    chain graph - on disk, for tests that exercise a full load through
    `run_platform` without needing the real (large) benchmark dataset.
    """
    nodes_path = tmp_path / "nodes.csv"
    edges_path = tmp_path / "edges.csv"
    with open(nodes_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "handle"])
        for i in range(10):
            w.writerow([str(i), f"user{i}"])
    with open(edges_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src", "dst"])
        for i in range(9):
            w.writerow([str(i), str(i + 1)])
    return nodes_path, edges_path


@pytest.fixture
def tiny_node_edge_records() -> tuple[list[NodeRecord], list[EdgeRecord]]:
    """The same 10-node chain as `small_dataset`, but already parsed into
    `NodeRecord`/`EdgeRecord` objects - handy for tests that call an
    adapter's `load_nodes`/`load_edges` directly instead of going through
    `run_platform` + CSV files.
    """
    nodes = [
        NodeRecord(node_id=str(i), label="Person", props={"handle": f"user{i}"}) for i in range(10)
    ]
    edges = [
        EdgeRecord(src_id=str(i), dst_id=str(i + 1), rel_type="FOLLOWS") for i in range(9)
    ]
    return nodes, edges


@pytest.fixture
def fake_registry() -> Iterator[dict]:
    """Yields the real ADAPTER_REGISTRY so a test can monkeypatch entries
    into it (e.g. register FakeAdapter under a throwaway name) with
    automatic cleanup afterwards, instead of every test hand-rolling that.
    """
    from benchmark.adapters import registry as adapter_registry

    original = dict(adapter_registry.ADAPTER_REGISTRY)
    try:
        yield adapter_registry.ADAPTER_REGISTRY
    finally:
        adapter_registry.ADAPTER_REGISTRY.clear()
        adapter_registry.ADAPTER_REGISTRY.update(original)