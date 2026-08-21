import uuid
import pytest
from neo4j import Driver

@pytest.mark.integration
@pytest.mark.cognodb
def test_cognodb_create_and_read_node(cognodb_driver: Driver) -> None:
    """
    Verify create, read, and cleanup operations.
    """

    test_id = f"pytest-{uuid.uuid4()}"

    try:
        with cognodb_driver.session() as session:

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
        with cognodb_driver.session() as session:

            session.run(
                """
                MATCH (n:BenchmarkTest {
                    id: $id
                })
                DELETE n
                """,
                id=test_id,
            ).consume()