import pytest

from benchmark.adapters.memgraph_adapter import (
    MemgraphAdapter,
)


@pytest.mark.memgraph
def test_memgraph_connection() -> None:
    adapter = MemgraphAdapter()

    try:
        adapter.connect()

        db = adapter._require_db()

        result = list(
            db.execute_and_fetch(
                "RETURN 1 AS value"
            )
        )

        assert result[0]["value"] == 1

    finally:
        adapter.close()