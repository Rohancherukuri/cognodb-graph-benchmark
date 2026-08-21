from __future__ import annotations

import csv
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

from benchmark.adapters.base import EdgeRecord, NodeRecord


# Load variables from the project's .env file.
load_dotenv()


@pytest.fixture(scope="session")
def cognodb_driver() -> Iterator[Driver]:
    """
    Shared Neo4j-compatible driver connected to CognoDB Cloud.

    The fixture is skipped when the required CognoDB credentials
    are not available, so the rest of the test suite can still run.
    """

    uri = os.environ.get("COGNODB_URI")
    user = os.environ.get("COGNODB_USER")
    password = os.environ.get("COGNODB_PASSWORD")

    if not uri:
        pytest.skip("COGNODB_URI is not configured.")

    if not user:
        pytest.skip("COGNODB_USER is not configured.")

    if not password:
        pytest.skip("COGNODB_PASSWORD is not configured.")

    driver = GraphDatabase.driver(
        uri,
        auth=(user, password),
    )

    try:
        yield driver
    finally:
        driver.close()


def pytest_configure(config: pytest.Config) -> None:
    """
    Register custom pytest markers used throughout the project.
    """

    config.addinivalue_line(
        "markers",
        (
            "live: hits a real, network-reachable graph database "
            "(needs credentials)"
        ),
    )

    config.addinivalue_line(
        "markers",
        (
            "network: needs outbound internet access "
            "(e.g. downloading a public dataset)"
        ),
    )

    config.addinivalue_line(
        "markers",
        "integration: runs an integration test against real components",
    )

    config.addinivalue_line(
        "markers",
        "cognodb: requires a CognoDB instance",
    )

    config.addinivalue_line(
        "markers",
        "arangodb: requires an ArangoDB instance",
    )

    config.addinivalue_line(
        "markers",
        "memgraph: requires a Memgraph instance",
    )

    config.addinivalue_line(
        "markers",
        "neo4j: requires a Neo4j instance",
    )

    config.addinivalue_line(
        "markers",
        "surrealdb: requires a SurrealDB instance",
    )


def requires_env(*names: str) -> pytest.MarkDecorator:
    """
    Skip a test unless every named environment variable is set
    and non-empty.

    Used to gate live credential tests so that the default
    pytest run does not require real database credentials.

    Example:

        @pytest.mark.live
        @requires_env("SURREALDB_URL", "SURREALDB_PASSWORD")
        def test_something_live():
            ...
    """

    missing = [
        name
        for name in names
        if not os.environ.get(name)
    ]

    return pytest.mark.skipif(
        bool(missing),
        reason=(
            "missing required env var(s) for a live test: "
            f"{', '.join(missing)}"
        ),
    )


@pytest.fixture
def small_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """
    Write a tiny deterministic graph dataset to disk.

    The dataset contains:

        Nodes:
            user0 -> user9

        Relationships:
            user0 -> user1
            user1 -> user2
            ...
            user8 -> user9

    This fixture is useful for tests that exercise a complete
    ingestion flow through run_platform without requiring the
    full Epinions benchmark dataset.
    """

    nodes_path = tmp_path / "nodes.csv"
    edges_path = tmp_path / "edges.csv"

    with open(nodes_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "id",
                "handle",
            ]
        )

        for i in range(10):
            writer.writerow(
                [
                    str(i),
                    f"user{i}",
                ]
            )

    with open(edges_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "src",
                "dst",
            ]
        )

        for i in range(9):
            writer.writerow(
                [
                    str(i),
                    str(i + 1),
                ]
            )

    return nodes_path, edges_path


@pytest.fixture
def tiny_node_edge_records() -> tuple[
    list[NodeRecord],
    list[EdgeRecord],
]:
    """
    Return the same 10-node chain graph as parsed NodeRecord
    and EdgeRecord objects.

    This is useful for adapter tests that directly call
    load_nodes() and load_edges() instead of going through
    CSV files and run_platform().
    """

    nodes = [
        NodeRecord(
            node_id=str(i),
            label="Person",
            props={
                "handle": f"user{i}",
            },
        )
        for i in range(10)
    ]

    edges = [
        EdgeRecord(
            src_id=str(i),
            dst_id=str(i + 1),
            rel_type="FOLLOWS",
        )
        for i in range(9)
    ]

    return nodes, edges


@pytest.fixture
def fake_registry() -> Iterator[dict]:
    """
    Yield the real ADAPTER_REGISTRY for temporary monkeypatching.

    The original registry is automatically restored after the test.
    """

    from benchmark.adapters import registry as adapter_registry

    original = dict(
        adapter_registry.ADAPTER_REGISTRY
    )

    try:
        yield adapter_registry.ADAPTER_REGISTRY

    finally:
        adapter_registry.ADAPTER_REGISTRY.clear()

        adapter_registry.ADAPTER_REGISTRY.update(
            original
        )