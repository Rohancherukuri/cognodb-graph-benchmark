from __future__ import annotations

import os
import random
import time
from typing import Iterable

from arango import ArangoClient
from dotenv import load_dotenv

from .base import (
    EdgeRecord,
    GraphDBAdapter,
    NodeRecord,
)


load_dotenv()


class ArangoDBAdapter(GraphDBAdapter):
    """
    ArangoDB Cloud adapter.

    Environment variables:
        ARANGODB_URL
        ARANGODB_USER
        ARANGODB_PASSWORD
        ARANGODB_DB
    """

    name = "arangodb"
    indexed_property = "handle"

    GRAPH_NAME = "social"

    def __init__(self) -> None:
        self.url = os.environ.get(
            "ARANGODB_URL"
        )

        self.user = os.environ.get(
            "ARANGODB_USER"
        )

        self.password = os.environ.get(
            "ARANGODB_PASSWORD"
        )

        self.db_name = os.environ.get(
            "ARANGODB_DB",
            "_system",
        )

        self._client: ArangoClient | None = None
        self._db = None

    def connect(self) -> None:
        """
        Connect directly to the configured
        ArangoDB Cloud database.
        """

        if self._db is not None:
            return

        if not self.url:
            raise RuntimeError(
                "ARANGODB_URL is not configured."
            )

        if not self.user:
            raise RuntimeError(
                "ARANGODB_USER is not configured."
            )

        if not self.password:
            raise RuntimeError(
                "ARANGODB_PASSWORD is not configured."
            )

        self._client = ArangoClient(
            hosts=self.url,
        )

        self._db = self._client.db(
            self.db_name,
            username=self.user,
            password=self.password,
        )

        # Force a connectivity/authentication check.
        self._db.version()

        self._ensure_collections()
        self._ensure_graph()

    def _require_db(self):
        if self._db is None:
            raise RuntimeError(
                "ArangoDB is not connected. "
                "Call connect() first."
            )

        return self._db

    def _ensure_collections(self) -> None:
        db = self._require_db()

        if not db.has_collection(
            "persons"
        ):
            db.create_collection(
                "persons"
            )

        if not db.has_collection(
            "follows"
        ):
            db.create_collection(
                "follows",
                edge=True,
            )

    def _ensure_graph(self) -> None:
        db = self._require_db()

        if not db.has_graph(
            self.GRAPH_NAME
        ):
            db.create_graph(
                self.GRAPH_NAME,
                edge_definitions=[
                    {
                        "edge_collection": "follows",
                        "from_vertex_collections": [
                            "persons"
                        ],
                        "to_vertex_collections": [
                            "persons"
                        ],
                    }
                ],
            )

    def close(self) -> None:
        """
        python-arango uses HTTP requests and does not
        require an explicit persistent connection close.
        """

        self._db = None
        self._client = None

    def clear(self) -> None:
        db = self._require_db()

        db.collection(
            "follows"
        ).truncate()

        db.collection(
            "persons"
        ).truncate()

    def create_indexes(self) -> None:
        db = self._require_db()

        collection = db.collection(
            "persons"
        )

        try:
            collection.add_persistent_index(
                fields=[
                    self.indexed_property
                ],
            )

        except Exception:
            # Most likely the index already exists.
            pass

    def load_nodes(
        self,
        nodes: Iterable[NodeRecord],
        batch_size: int,
    ) -> int:
        db = self._require_db()

        collection = db.collection(
            "persons"
        )

        batch: list[dict] = []
        total = 0

        for node in nodes:
            batch.append(
                {
                    "_key": node.node_id,
                    "handle": node.props.get(
                        "handle",
                        node.node_id,
                    ),
                }
            )

            if len(batch) >= batch_size:
                collection.insert_many(
                    batch,
                    overwrite=True,
                )

                total += len(batch)
                batch = []

        if batch:
            collection.insert_many(
                batch,
                overwrite=True,
            )

            total += len(batch)

        return total

    def load_edges(
        self,
        edges: Iterable[EdgeRecord],
        batch_size: int,
    ) -> int:
        db = self._require_db()

        collection = db.collection(
            "follows"
        )

        batch: list[dict] = []
        total = 0

        for edge in edges:
            batch.append(
                {
                    "_from": (
                        f"persons/{edge.src_id}"
                    ),
                    "_to": (
                        f"persons/{edge.dst_id}"
                    ),
                }
            )

            if len(batch) >= batch_size:
                collection.insert_many(
                    batch,
                    overwrite=True,
                )

                total += len(batch)
                batch = []

        if batch:
            collection.insert_many(
                batch,
                overwrite=True,
            )

            total += len(batch)

        return total

    def traversal(
        self,
        start_id: str,
        hops: int,
    ) -> float:
        if hops <= 0:
            raise ValueError(
                "hops must be greater than zero."
            )

        db = self._require_db()

        aql = (
            "FOR v IN @hops..@hops "
            "OUTBOUND @start "
            "GRAPH @graph "
            "COLLECT WITH COUNT INTO count "
            "RETURN count"
        )

        t0 = time.perf_counter()

        cursor = db.aql.execute(
            aql,
            bind_vars={
                "start": (
                    f"persons/{start_id}"
                ),
                "hops": hops,
                "graph": self.GRAPH_NAME,
            },
        )

        list(cursor)

        return (
            time.perf_counter() - t0
        ) * 1000

    def point_lookup(
        self,
        node_id: str,
    ) -> float:
        db = self._require_db()

        t0 = time.perf_counter()

        db.collection(
            "persons"
        ).get(node_id)

        return (
            time.perf_counter() - t0
        ) * 1000

    def indexed_lookup(
        self,
        value: str,
    ) -> float:
        db = self._require_db()

        aql = (
            "FOR p IN persons "
            f"FILTER p.{self.indexed_property} == @value "
            "RETURN p"
        )

        t0 = time.perf_counter()

        list(
            db.aql.execute(
                aql,
                bind_vars={
                    "value": value,
                },
            )
        )

        return (
            time.perf_counter() - t0
        ) * 1000

    def aggregation(self) -> float:
        db = self._require_db()

        aql = """
        FOR edge IN follows
            COLLECT
                source = edge._from
                WITH COUNT INTO out_degree
            SORT out_degree DESC
            LIMIT 100
            RETURN {
                source: source,
                out_degree: out_degree
            }
        """

        t0 = time.perf_counter()

        list(
            db.aql.execute(aql)
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

            db.collection(
                "persons"
            ).get(node_id)

        else:
            node_id = (
                f"mixed-"
                f"{random.randint(0, 10_000_000)}"
            )

            db.collection(
                "persons"
            ).insert(
                {
                    "_key": node_id,
                    "handle": node_id,
                    "mixed": True,
                },
                overwrite=True,
            )

        return (
            time.perf_counter() - t0
        ) * 1000

    def footprint(self) -> dict:
        try:
            db = self._require_db()

            persons = db.collection(
                "persons"
            )

            follows = db.collection(
                "follows"
            )

            return {
                "node_count": persons.count(),
                "rel_count": follows.count(),
            }

        except Exception as exc:
            return {
                "error": str(exc),
                "note": (
                    "Collection statistics are not "
                    "available for this deployment."
                ),
            }