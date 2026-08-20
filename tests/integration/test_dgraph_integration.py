import json

import pytest

from benchmark.adapters.base import (
    EdgeRecord,
    NodeRecord,
)
from benchmark.adapters.dgraph_adapter import (
    DgraphAdapter,
)


@pytest.mark.integration
@pytest.mark.dgraph
def test_dgraph_create_and_read_graph() -> None:
    adapter = DgraphAdapter()

    nodes = [
        NodeRecord(
            node_id="1",
            label="Person",
            props={
                "handle": "alice",
            },
        ),
        NodeRecord(
            node_id="2",
            label="Person",
            props={
                "handle": "bob",
            },
        ),
        NodeRecord(
            node_id="3",
            label="Person",
            props={
                "handle": "charlie",
            },
        ),
    ]

    edges = [
        EdgeRecord(
            src_id="1",
            dst_id="2",
            rel_type="FOLLOWS",
        ),
        EdgeRecord(
            src_id="1",
            dst_id="3",
            rel_type="FOLLOWS",
        ),
        EdgeRecord(
            src_id="2",
            dst_id="3",
            rel_type="FOLLOWS",
        ),
    ]

    try:
        # ----------------------------------------------------
        # Connect
        # ----------------------------------------------------

        adapter.connect()

        # ----------------------------------------------------
        # Reset database
        # ----------------------------------------------------

        adapter.clear()

        # clear() removes schema as well.
        adapter.create_indexes()

        # ----------------------------------------------------
        # Load nodes
        # ----------------------------------------------------

        loaded_nodes = adapter.load_nodes(
            nodes,
            batch_size=2,
        )

        assert loaded_nodes == 3

        # ----------------------------------------------------
        # Load relationships
        # ----------------------------------------------------

        loaded_edges = adapter.load_edges(
            edges,
            batch_size=2,
        )

        assert loaded_edges == 3

        client = adapter._require_client()

        # ----------------------------------------------------
        # Verify node count
        # ----------------------------------------------------

        node_query = """
        {
            nodes(func: has(external_id)) {
                uid
            }
        }
        """

        node_response = client.txn(
            read_only=True
        ).query(node_query)

        node_data = json.loads(
            node_response.json
        )

        assert len(
            node_data["nodes"]
        ) == 3

        # ----------------------------------------------------
        # Verify relationship count
        # ----------------------------------------------------

        edge_query = """
        {
            nodes(func: has(follows)) {
                count(follows)
            }
        }
        """

        edge_response = client.txn(
            read_only=True
        ).query(edge_query)

        edge_data = json.loads(
            edge_response.json
        )

        relationship_count = sum(
            node.get(
                "count(follows)",
                0,
            )
            for node in edge_data["nodes"]
        )

        assert relationship_count == 3

        # ----------------------------------------------------
        # Verify point lookup
        # ----------------------------------------------------

        lookup_query = """
        query q($id: string) {
            q(
                func: eq(
                    external_id,
                    $id
                )
            ) {
                external_id
                handle
            }
        }
        """

        lookup_response = client.txn(
            read_only=True
        ).query(
            lookup_query,
            variables={
                "$id": "1",
            },
        )

        lookup_data = json.loads(
            lookup_response.json
        )

        assert len(
            lookup_data["q"]
        ) == 1

        assert (
            lookup_data["q"][0]["handle"]
            == "alice"
        )

        # ----------------------------------------------------
        # Verify adapter benchmark operations
        # ----------------------------------------------------

        traversal_ms = adapter.traversal(
            start_id="1",
            hops=1,
        )

        assert traversal_ms >= 0

        point_lookup_ms = adapter.point_lookup(
            node_id="1",
        )

        assert point_lookup_ms >= 0

        indexed_lookup_ms = adapter.indexed_lookup(
            value="alice",
        )

        assert indexed_lookup_ms >= 0

        aggregation_ms = adapter.aggregation()

        assert aggregation_ms >= 0

        read_ms = adapter.mixed_op(
            is_read=True,
        )

        assert read_ms >= 0

        write_ms = adapter.mixed_op(
            is_read=False,
        )

        assert write_ms >= 0

        # ----------------------------------------------------
        # Verify graph counts
        # ----------------------------------------------------

        footprint = adapter.footprint()

        assert (
            footprint["node_count"]
            >= 3
        )

        assert (
            footprint["rel_count"]
            == 3
        )

    finally:
        adapter.close()