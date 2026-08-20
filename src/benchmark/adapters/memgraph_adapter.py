from __future__ import annotations

import os
from dotenv import load_dotenv
from .bolt_cypher_adapter import BoltCypherAdapter

load_dotenv()  # load env vars from .env file in project root

class MemgraphAdapter(BoltCypherAdapter):
    """Memgraph, self-hosted via docker-compose and capped to the same
    vCPU/RAM as CognoDB's free tier (see docker-compose.yml). Memgraph also
    speaks Bolt + Cypher, so it reuses BoltCypherAdapter unchanged.

    Env vars: MEMGRAPH_URI (default bolt://localhost:7688), MEMGRAPH_USER,
    MEMGRAPH_PASSWORD (both optional - community Memgraph has no auth by
    default).
    """

    name = "memgraph"

    def __init__(self) -> None:
        super().__init__(
            uri=os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688"),
            user=os.environ.get("MEMGRAPH_USER", ""),
            password=os.environ.get("MEMGRAPH_PASSWORD", ""),
        )
