import uuid

import pytest

from benchmark.adapters.neo4j_aura_adapter import (
    Neo4jAuraAdapter,
)


@pytest.mark.integration
@pytest.mark.neo4j
def test_neo4j_create_and_read_node() -> None:
    adapter = Neo4jAuraAdapter()

    test_id = f"pytest-{uuid.uuid4()}"

    try:
        adapter.connect()

        with adapter._session() as session:
            session.run(
                """
                CREATE (:BenchmarkTest {
                    id: $id
                })
                """,
                id=test_id,
            ).consume()

            result = session.run(
                """
                MATCH (n:BenchmarkTest {
                    id: $id
                })
                RETURN n.id AS id
                """,
                id=test_id,
            )

            record = result.single()

            assert record is not None
            assert record["id"] == test_id

    finally:
        try:
            with adapter._session() as session:
                session.run(
                    """
                    MATCH (n:BenchmarkTest {
                        id: $id
                    })
                    DELETE n
                    """,
                    id=test_id,
                ).consume()
        finally:
            adapter.close()