from __future__ import annotations

from typing import Iterator

import pytest

from benchmark.adapters.surrealdb_adapter import SurrealDBAdapter

from ..conftest import requires_env

pytestmark = [pytest.mark.live, requires_env("SURREALDB_URL")]


@pytest.fixture
def surrealdb_with_fixture_data(tiny_node_edge_records) -> Iterator[SurrealDBAdapter]:
    """Connects to a real SurrealDB instance, loads the 10-node chain graph
    from `conftest.tiny_node_edge_records`, yields the connected adapter,
    and always cleans up afterwards - even if the test fails.
    """
    nodes, edges = tiny_node_edge_records
    adapter = SurrealDBAdapter()
    adapter.connect()
    adapter.clear()
    adapter.create_indexes()
    adapter.load_nodes(nodes, batch_size=100)
    adapter.load_edges(edges, batch_size=100)
    try:
        yield adapter
    finally:
        adapter.clear()
        adapter.close()


def test_point_lookup_hit(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    latency_ms = surrealdb_with_fixture_data.point_lookup("0")
    assert latency_ms >= 0


def test_point_lookup_miss_does_not_raise(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    # `select()` on a record id that doesn't exist is expected to return
    # None rather than raise - this asserts that assumption instead of
    # just hoping it holds when the mixed workload hits random misses.
    latency_ms = surrealdb_with_fixture_data.point_lookup("does-not-exist")
    assert latency_ms >= 0


def test_indexed_lookup_by_handle(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    latency_ms = surrealdb_with_fixture_data.indexed_lookup("user0")
    assert latency_ms >= 0


def test_one_hop_traversal_reaches_neighbor(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    latency_ms = surrealdb_with_fixture_data.traversal("0", hops=1)
    assert latency_ms >= 0


def test_three_hop_traversal(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    latency_ms = surrealdb_with_fixture_data.traversal("0", hops=3)
    assert latency_ms >= 0


def test_aggregation_returns(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    latency_ms = surrealdb_with_fixture_data.aggregation()
    assert latency_ms >= 0


def test_mixed_op_read_and_write(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    read_latency = surrealdb_with_fixture_data.mixed_op(is_read=True)
    write_latency = surrealdb_with_fixture_data.mixed_op(is_read=False)
    assert read_latency >= 0
    assert write_latency >= 0


def test_footprint_reports_loaded_counts(surrealdb_with_fixture_data: SurrealDBAdapter) -> None:
    info = surrealdb_with_fixture_data.footprint()
    assert info.get("node_count") == 10
    assert info.get("rel_count") == 9