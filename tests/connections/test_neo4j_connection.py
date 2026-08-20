import pytest

from benchmark.adapters.neo4j_aura_adapter import (
    Neo4jAuraAdapter,
)


@pytest.mark.neo4j
def test_neo4j_connection() -> None:
    adapter = Neo4jAuraAdapter()

    try:
        adapter.connect()

        assert adapter._driver is not None

    finally:
        adapter.close()