from neo4j import Driver

def test_cognodb_can_execute_query(cognodb_driver: Driver) -> None:
    """
    Verify that CognoDB can execute a basic Cypher query.
    """

    with cognodb_driver.session() as session:

        result = session.run(
            "RETURN 1 AS value"
        )

        record = result.single()

    assert record is not None
    assert record["value"] == 1