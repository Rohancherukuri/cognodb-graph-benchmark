from __future__ import annotations

import os
from dotenv import load_dotenv
from .bolt_cypher_adapter import BoltCypherAdapter

load_dotenv()  # load env vars from .env file in project root

class CognoDBAdapter(BoltCypherAdapter):
    """CognoDB Cloud - per the assignment's setup steps, this is a Bolt +
    Cypher endpoint reachable with the official Neo4j driver.

    Required env vars: COGNODB_URI, COGNODB_PASSWORD (COGNODB_USER defaults
    to "cognodb" as documented).
    """

    name = "cognodb"

    def __init__(self) -> None:
        super().__init__(
            uri=os.environ.get("COGNODB_URI"),
            user=os.environ.get("COGNODB_USER", "cognodb"),
            password=os.environ.get("COGNODB_PASSWORD"),
        )
