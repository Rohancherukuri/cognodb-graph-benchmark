import pytest

from benchmark.adapters.neo4j_aura_adapter import (
    Neo4jAuraAdapter,
)


@pytest.mark.neo4j
def test_neo4j_can_execute_query() -> None:
    adapter = Neo4jAuraAdapter()

    try:
        adapter.connect()

        with adapter._session() as session:
            result = session.run(
                "RETURN 1 AS value"
            )

            record = result.single()

        assert record is not None
        assert record["value"] == 1

    finally:
        adapter.close()