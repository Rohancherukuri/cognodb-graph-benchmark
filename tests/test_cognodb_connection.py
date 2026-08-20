import os
import pytest
from neo4j import Driver


def test_cognodb_connectivity(cognodb_driver: Driver) -> None:
    """
    Verify that the benchmark environment can connect
    to CognoDB Cloud.
    """

    cognodb_driver.verify_connectivity()