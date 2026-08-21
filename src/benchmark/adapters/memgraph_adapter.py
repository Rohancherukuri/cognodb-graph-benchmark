from __future__ import annotations

import os
import random
import time
from typing import Iterable

from dotenv import load_dotenv
from gqlalchemy import Memgraph

from .base import EdgeRecord, GraphDBAdapter, NodeRecord


load_dotenv()


class MemgraphAdapter(GraphDBAdapter):
    """
    Memgraph Cloud adapter using the official GQLAlchemy SDK.

    Environment variables:
        MEMGRAPH_HOST
        MEMGRAPH_PORT
        MEMGRAPH_USER
        MEMGRAPH_PASSWORD
        MEMGRAPH_ENCRYPTED
    """

    name = "memgraph"
    indexed_property = "handle"

    def __init__(self) -> None:
        self.host = os.environ.get("MEMGRAPH_HOST")

        self.port = int(
            os.environ.get(
                "MEMGRAPH_PORT",
                "7687",
            )
        )

        self.user = os.environ.get(
            "MEMGRAPH_USER",
            "",
        )

        self.password = os.environ.get(
            "MEMGRAPH_PASSWORD",
            "",
        )

        self.encrypted = (
            os.environ.get(
                "MEMGRAPH_ENCRYPTED",
                "true",
            ).lower()
            == "true"
        )

        self._db: Memgraph | None = None

    def connect(self) -> None:
        """
        Establish a connection to Memgraph Cloud.
        """

        if self._db is not None:
            return

        if not self.host:
            raise RuntimeError(
                "MEMGRAPH_HOST is not configured."
            )

        self._db = Memgraph(
            self.host,
            self.port,
            self.user,
            self.password,
            encrypted=self.encrypted,
        )

        # Force an actual connectivity check.
        list(
            self._db.execute_and_fetch(
                "RETURN 1 AS value"
            )
        )

    def close(self) -> None:
        """
        Release the adapter reference.

        GQLAlchemy manages the underlying connection.
        """

        self._db = None

    def _require_db(self) -> Memgraph:
        if self._db is None:
            raise RuntimeError(
                "Memgraph is not connected. "
                "Call connect() first."
            )

        return self._db

    def _execute(self, query: str, **params) -> None:
        db = self._require_db()

        list(
            db.execute_and_fetch(
                query,
                parameters=params or None,
            )
        )
        
    def clear(self) -> None:
        self._execute(
            "MATCH (n) DETACH DELETE n"
        )

    def create_indexes(self) -> None:
        """
        Create an index on the benchmark lookup property.
        """

        try:
            self._execute(
                f"CREATE INDEX ON :Person({self.indexed_property})"
            )

        except Exception:
            # The index may already exist.
            pass

    def load_nodes(
        self,
        nodes: Iterable[NodeRecord],
        batch_size: int,
    ) -> int:
        batch: list[dict] = []
        total = 0

        for node in nodes:
            batch.append(
                {
                    "id": node.node_id,
                    "handle": node.props.get(
                        "handle",
                        node.node_id,
                    ),
                }
            )

            if len(batch) >= batch_size:
                self._flush_nodes(batch)

                total += len(batch)
                batch = []

        if batch:
            self._flush_nodes(batch)
            total += len(batch)

        return total

    def _flush_nodes(
        self,
        batch: list[dict],
    ) -> None:
        self._execute(
            """
            UNWIND $rows AS row
            MERGE (p:Person {id: row.id})
            SET p.handle = row.handle
            """,
            rows=batch,
        )

    def load_edges(
        self,
        edges: Iterable[EdgeRecord],
        batch_size: int,
    ) -> int:
        batch: list[dict] = []
        total = 0

        for edge in edges:
            batch.append(
                {
                    "src": edge.src_id,
                    "dst": edge.dst_id,
                }
            )

            if len(batch) >= batch_size:
                self._flush_edges(batch)

                total += len(batch)
                batch = []

        if batch:
            self._flush_edges(batch)
            total += len(batch)

        return total

    def _flush_edges(
        self,
        batch: list[dict],
    ) -> None:
        self._execute(
            """
            UNWIND $rows AS row
            MATCH (a:Person {id: row.src})
            MATCH (b:Person {id: row.dst})
            MERGE (a)-[:FOLLOWS]->(b)
            """,
            rows=batch,
        )

    def traversal(
        self,
        start_id: str,
        hops: int,
    ) -> float:
        if hops <= 0:
            raise ValueError(
                "hops must be greater than zero."
            )

        query = (
            f"MATCH (p:Person {{id: $id}})"
            f"-[:FOLLOWS*{hops}]->(n) "
            "RETURN count(DISTINCT n) AS c"
        )

        db = self._require_db()

        t0 = time.perf_counter()

        list(
            db.execute_and_fetch(
                query,
                parameters={
                    "id": start_id,
                },
            )
        )

        return (
            time.perf_counter() - t0
        ) * 1000

    def point_lookup(
        self,
        node_id: str,
    ) -> float:
        db = self._require_db()

        t0 = time.perf_counter()

        list(
            db.execute_and_fetch(
                """
                MATCH (p:Person {id: $id})
                RETURN p
                """,
                parameters={
                    "id": node_id,
                },
            )
        )

        return (
            time.perf_counter() - t0
        ) * 1000

    def indexed_lookup(
        self,
        value: str,
    ) -> float:
        db = self._require_db()

        t0 = time.perf_counter()

        list(
            db.execute_and_fetch(
                f"""
                MATCH (p:Person {{
                    {self.indexed_property}: $value
                }})
                RETURN p
                """,
                parameters={
                    "value": value,
                },
            )
        )

        return (
            time.perf_counter() - t0
        ) * 1000

    def aggregation(self) -> float:
        db = self._require_db()

        t0 = time.perf_counter()

        list(
            db.execute_and_fetch(
                """
                MATCH (p:Person)-[:FOLLOWS]->(n)
                RETURN
                    p.id AS id,
                    count(n) AS out_degree
                ORDER BY out_degree DESC
                LIMIT 100
                """
            )
        )

        return (
            time.perf_counter() - t0
        ) * 1000

    def mixed_op(
        self,
        is_read: bool,
    ) -> float:
        db = self._require_db()

        t0 = time.perf_counter()

        if is_read:
            node_id = str(
                random.randint(
                    0,
                    75_878,
                )
            )

            list(
                db.execute_and_fetch(
                    """
                    MATCH (p:Person {id: $id})
                    RETURN p
                    """,
                    parameters={
                        "id": node_id,
                    },
                )
            )

        else:
            node_id = (
                f"mixed-"
                f"{random.randint(0, 10_000_000)}"
            )

            list(
                db.execute_and_fetch(
                    """
                    MERGE (p:Person {id: $id})
                    SET
                        p.handle = $id,
                        p.mixed = true
                    """,
                    parameters={
                        "id": node_id,
                    },
                )
            )

        return (
            time.perf_counter() - t0
        ) * 1000

    def footprint(self) -> dict:
        try:
            db = self._require_db()

            result = list(
                db.execute_and_fetch(
                    """
                    MATCH (n)
                    OPTIONAL MATCH ()-[r]->()
                    RETURN
                        count(DISTINCT n) AS node_count,
                        count(r) AS rel_count
                    """
                )
            )

            if not result:
                return {
                    "node_count": 0,
                    "rel_count": 0,
                }

            return result[0]

        except Exception as exc:
            return {
                "error": str(exc),
            }