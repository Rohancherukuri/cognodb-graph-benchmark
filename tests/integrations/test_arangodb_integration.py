import uuid

import pytest

from benchmark.adapters.arangodb_adapter import (
    ArangoDBAdapter,
)


@pytest.mark.integration
@pytest.mark.arangodb
def test_arangodb_create_and_read_node() -> None:
    adapter = ArangoDBAdapter()

    test_id = f"pytest-{uuid.uuid4()}"

    try:
        adapter.connect()

        db = adapter._require_db()

        collection = db.collection(
            "persons"
        )

        collection.insert(
            {
                "_key": test_id,
                "handle": test_id,
                "test": True,
            }
        )

        document = collection.get(
            test_id
        )

        assert document is not None
        assert document["_key"] == test_id
        assert document["test"] is True

    finally:
        try:
            if adapter._db is not None:
                adapter._db.collection(
                    "persons"
                ).delete(
                    test_id,
                    ignore_missing=True,
                )
        finally:
            adapter.close()