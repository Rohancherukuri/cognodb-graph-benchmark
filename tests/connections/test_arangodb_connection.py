import pytest

from benchmark.adapters.arangodb_adapter import (
    ArangoDBAdapter,
)


@pytest.mark.integration
@pytest.mark.arangodb
def test_arangodb_connection() -> None:
    adapter = ArangoDBAdapter()

    try:
        adapter.connect()

        assert adapter._db is not None

        result = list(
            adapter._db.aql.execute(
                "RETURN 1"
            )
        )

        assert result == [1]

    finally:
        adapter.close()