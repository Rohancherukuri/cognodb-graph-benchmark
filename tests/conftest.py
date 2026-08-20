import os
import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

@pytest.fixture(scope="session")
def cognodb_driver():
    """
    Shared Neo4j-compatible driver connected to
    CognoDB Cloud.
    """

    uri = os.environ.get("COGNODB_URI")
    user = os.environ.get("COGNODB_USER")
    password = os.environ.get("COGNODB_PASSWORD")

    if not uri:
        pytest.skip(
            "COGNODB_URI is not configured."
        )

    if not user:
        pytest.skip(
            "COGNODB_USER is not configured."
        )

    if not password:
        pytest.skip(
            "COGNODB_PASSWORD is not configured."
        )

    driver = GraphDatabase.driver(
        uri,
        auth=(user, password),
    )

    try:
        yield driver

    finally:
        driver.close()