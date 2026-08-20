import pytest

from benchmark.adapters.dgraph_adapter import (
    DgraphAdapter,
)


@pytest.mark.dgraph
def test_dgraph_connection() -> None:
    adapter = DgraphAdapter()

    try:
        adapter.connect()

        client = adapter._require_client()

        response = client.txn(
            read_only=True
        ).query(
            """
            {
                q(func: uid(0x1)) {
                    uid
                }
            }
            """
        )

        assert response is not None

    finally:
        adapter.close()