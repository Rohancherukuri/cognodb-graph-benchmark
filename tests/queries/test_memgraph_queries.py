import pytest

from benchmark.adapters.memgraph_adapter import (
    MemgraphAdapter,
)


@pytest.mark.memgraph
def test_memgraph_can_execute_query() -> None:
    adapter = MemgraphAdapter()

    try:
        adapter.connect()

        db = adapter._require_db()

        results = list(
            db.execute_and_fetch(
                """
                RETURN
                    1 AS value,
                    "memgraph" AS database
                """
            )
        )

        assert results[0]["value"] == 1
        assert results[0]["database"] == "memgraph"

    finally:
        adapter.close()