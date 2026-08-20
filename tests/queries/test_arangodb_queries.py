import pytest

from benchmark.adapters.arangodb_adapter import (
    ArangoDBAdapter,
)


@pytest.mark.arangodb
def test_arangodb_can_execute_query() -> None:
    adapter = ArangoDBAdapter()

    try:
        adapter.connect()

        db = adapter._require_db()

        result = list(
            db.aql.execute(
                """
                RETURN {
                    value: 1,
                    database: "arangodb"
                }
                """
            )
        )

        assert result[0]["value"] == 1
        assert result[0]["database"] == "arangodb"

    finally:
        adapter.close()