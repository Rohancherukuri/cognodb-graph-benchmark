from __future__ import annotations

from .arangodb_adapter import ArangoDBAdapter
from .cognodb_adapter import CognoDBAdapter
from .memgraph_adapter import MemgraphAdapter
from .neo4j_aura_adapter import Neo4jAuraAdapter
from .surrealdb_adapter import SurrealDBAdapter

ADAPTER_REGISTRY = {
    "cognodb": CognoDBAdapter,
    "neo4j_aura": Neo4jAuraAdapter,
    "memgraph": MemgraphAdapter,
    "arangodb": ArangoDBAdapter,
    "surrealdb": SurrealDBAdapter,
}
