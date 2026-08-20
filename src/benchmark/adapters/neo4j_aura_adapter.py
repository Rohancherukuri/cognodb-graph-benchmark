from __future__ import annotations

import os
from dotenv import load_dotenv
from .bolt_cypher_adapter import BoltCypherAdapter

load_dotenv()  # load env vars from .env file in project root


class Neo4jAuraAdapter(BoltCypherAdapter):
    """Neo4j AuraDB Free - the natural direct comparison for CognoDB since
    both speak the same Bolt/Cypher protocol via the same driver, isolating
    the comparison to the platforms themselves rather than the client code.

    Required env vars: NEO4J_AURA_URI, NEO4J_AURA_PASSWORD
    (NEO4J_AURA_USER defaults to "neo4j").
    """

    name = "neo4j_aura"

    def __init__(self) -> None:
        super().__init__(
            uri=os.environ.get("NEO4J_AURA_URI"),
            user=os.environ.get("NEO4J_AURA_USER", "neo4j"),
            password=os.environ.get("NEO4J_AURA_PASSWORD"),
        )
