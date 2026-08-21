from __future__ import annotations

import uuid

import pytest

from benchmark.adapters.memgraph_adapter import (
    MemgraphAdapter,
)


@pytest.mark.integration
@pytest.mark.memgraph
def test_memgraph_create_and_read_node() -> None:
    adapter = MemgraphAdapter()

    test_id = f"pytest-{uuid.uuid4()}"

    try:
        adapter.connect()

        db = adapter._require_db()

        created = list(
            db.execute_and_fetch(
                """
                CREATE (
                    n:BenchmarkTest {
                        id: $id
                    }
                )
                RETURN n.id AS id
                """,
                parameters={
                    "id": test_id,
                },
            )
        )

        assert len(created) == 1
        assert created[0]["id"] == test_id

        results = list(
            db.execute_and_fetch(
                """
                MATCH (
                    n:BenchmarkTest {
                        id: $id
                    }
                )
                RETURN n.id AS id
                """,
                parameters={
                    "id": test_id,
                },
            )
        )

        assert len(results) == 1
        assert results[0]["id"] == test_id

    finally:
        try:
            if adapter._db is not None:
                list(
                    adapter._db.execute_and_fetch(
                        """
                        MATCH (
                            n:BenchmarkTest {
                                id: $id
                            }
                        )
                        DELETE n
                        RETURN count(*) AS deleted_count
                        """,
                        parameters={
                            "id": test_id,
                        },
                    )
                )

        finally:
            adapter.close()