from __future__ import annotations

import random
import time
from typing import Iterable, Optional

from neo4j import GraphDatabase, basic_auth

from .base import EdgeRecord, GraphDBAdapter, NodeRecord


class BoltCypherAdapter(GraphDBAdapter):
    """Shared implementation for any platform that speaks Bolt + Cypher.

    CognoDB Cloud, Neo4j AuraDB, and Memgraph are all driven through the
    official `neo4j` Python driver per the assignment's own setup steps
    ("Connect with an official Neo4j driver ... No other code changes are
    needed"). Subclasses only supply connection parameters; the query logic
    lives here once so all three platforms genuinely run identical queries.
    """

    indexed_property = "handle"

    def __init__(self, 
                 uri: str, 
                 user: str, 
                 password: str, 
                 database: Optional[str] = None
                 ) -> None:
        
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver = None

    def connect(self) -> None:
        self._driver = GraphDatabase.driver(self.uri, auth=basic_auth(self.user, self.password))
        self._driver.verify_connectivity()

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def _session(self):
        if self.database:
            return self._driver.session(database=self.database)
        return self._driver.session()

    def clear(self) -> None:
        with self._session() as s:
            s.run("MATCH (n) DETACH DELETE n").consume()

    def create_indexes(self) -> None:
        with self._session() as s:
            # Try modern syntax first (Neo4j 5 / recent Memgraph), then fall
            # back to older syntax so this works across all three platforms.
            try:
                s.run(
                    f"CREATE INDEX person_{self.indexed_property} IF NOT EXISTS "
                    f"FOR (p:Person) ON (p.{self.indexed_property})"
                ).consume()
            except Exception:
                try:
                    s.run(f"CREATE INDEX ON :Person({self.indexed_property})").consume()
                except Exception:
                    pass  # index creation is best-effort; record as a caveat upstream if it matters

    def load_nodes(self, nodes: Iterable[NodeRecord], batch_size: int) -> int:
        batch: list[dict] = []
        total = 0
        with self._session() as s:
            for n in nodes:
                batch.append({"id": n.node_id, "handle": n.props.get("handle", n.node_id)})
                if len(batch) >= batch_size:
                    total += self._flush_nodes(s, batch)
                    batch = []
            if batch:
                total += self._flush_nodes(s, batch)
        return total

    @staticmethod
    def _flush_nodes(session, batch: list[dict]) -> int:
        session.run(
            "UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p.handle = row.handle",
            rows=batch,
        ).consume()
        return len(batch)

    def load_edges(self, edges: Iterable[EdgeRecord], batch_size: int) -> int:
        batch: list[dict] = []
        total = 0
        with self._session() as s:
            for e in edges:
                batch.append({"src": e.src_id, "dst": e.dst_id})
                if len(batch) >= batch_size:
                    total += self._flush_edges(s, batch)
                    batch = []
            if batch:
                total += self._flush_edges(s, batch)
        return total

    @staticmethod
    def _flush_edges(session, batch: list[dict]) -> int:
        session.run(
            "UNWIND $rows AS row "
            "MATCH (a:Person {id: row.src}), (b:Person {id: row.dst}) "
            "MERGE (a)-[:FOLLOWS]->(b)",
            rows=batch,
        ).consume()
        return len(batch)

    def traversal(self, start_id: str, hops: int) -> float:
        query = (
            f"MATCH (p:Person {{id: $id}})-[:FOLLOWS*{hops}]->(n) "
            "RETURN count(DISTINCT n) AS c"
        )
        with self._session() as s:
            t0 = time.perf_counter()
            s.run(query, id=start_id).consume()
            return (time.perf_counter() - t0) * 1000

    def point_lookup(self, node_id: str) -> float:
        with self._session() as s:
            t0 = time.perf_counter()
            s.run("MATCH (p:Person {id: $id}) RETURN p", id=node_id).consume()
            return (time.perf_counter() - t0) * 1000

    def indexed_lookup(self, value: str) -> float:
        with self._session() as s:
            t0 = time.perf_counter()
            s.run(
                f"MATCH (p:Person {{{self.indexed_property}: $v}}) RETURN p", v=value
            ).consume()
            return (time.perf_counter() - t0) * 1000

    def aggregation(self) -> float:
        with self._session() as s:
            t0 = time.perf_counter()
            s.run(
                "MATCH (p:Person)-[:FOLLOWS]->(n) "
                "RETURN p.id AS id, count(n) AS out_degree "
                "ORDER BY out_degree DESC LIMIT 100"
            ).consume()
            return (time.perf_counter() - t0) * 1000

    def mixed_op(self, is_read: bool) -> float:
        with self._session() as s:
            t0 = time.perf_counter()
            if is_read:
                rid = str(random.randint(0, 1_000_000))
                s.run("MATCH (p:Person {id: $id}) RETURN p", id=rid).consume()
            else:
                rid = f"mixed-{random.randint(0, 10_000_000)}"
                s.run(
                    "MERGE (p:Person {id: $id}) SET p.handle = $id, p.mixed = true", id=rid
                ).consume()
            return (time.perf_counter() - t0) * 1000

    def footprint(self) -> dict:
        info: dict = {}
        try:
            with self._session() as s:
                rec = s.run(
                    "CALL apoc.meta.stats() YIELD nodeCount, relCount "
                    "RETURN nodeCount, relCount"
                ).single()
                if rec:
                    info["node_count"] = rec["nodeCount"]
                    info["rel_count"] = rec["relCount"]
        except Exception:
            try:
                with self._session() as s:
                    n = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
                    r = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
                    info["node_count"], info["rel_count"] = n, r
            except Exception as exc:
                info["error"] = str(exc)
        info.setdefault(
            "note",
            "stored-data size / memory usage not exposed via Bolt on managed free tiers; "
            "see each platform's console for whatever it surfaces.",
        )
        return info
