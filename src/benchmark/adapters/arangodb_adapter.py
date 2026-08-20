from __future__ import annotations

import os
import random
import time
from typing import Iterable
from dotenv import load_dotenv
from arango import ArangoClient

from .base import EdgeRecord, GraphDBAdapter, NodeRecord

load_dotenv()  # load env vars from .env file in project root

class ArangoDBAdapter(GraphDBAdapter):
    """ArangoDB, self-hosted via docker-compose and capped to the same
    vCPU/RAM as CognoDB's free tier. Uses the `persons` vertex collection
    and `follows` edge collection inside a named graph, queried with AQL.

    Env vars: ARANGODB_URL, ARANGODB_USER, ARANGODB_PASSWORD, ARANGODB_DB.
    """

    name = "arangodb"
    indexed_property = "handle"
    GRAPH_NAME = "social"

    def __init__(self) -> None:
        self.url = os.environ.get("ARANGODB_URL", "http://localhost:8529")
        self.user = os.environ.get("ARANGODB_USER", "root")
        self.password = os.environ.get("ARANGODB_PASSWORD", "")
        self.db_name = os.environ.get("ARANGODB_DB", "benchmark")
        self._client = None
        self._db = None

    def connect(self) -> None:
        self._client = ArangoClient(hosts=self.url)
        sys_db = self._client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.db_name):
            sys_db.create_database(self.db_name)
        self._db = self._client.db(self.db_name, username=self.user, password=self.password)
        if not self._db.has_collection("persons"):
            self._db.create_collection("persons")
        if not self._db.has_collection("follows"):
            self._db.create_collection("follows", edge=True)
        if not self._db.has_graph(self.GRAPH_NAME):
            self._db.create_graph(
                self.GRAPH_NAME,
                edge_definitions=[
                    {
                        "edge_collection": "follows",
                        "from_vertex_collections": ["persons"],
                        "to_vertex_collections": ["persons"],
                    }
                ],
            )

    def close(self) -> None:
        pass  # python-arango uses per-request HTTP sessions; nothing to close explicitly

    def clear(self) -> None:
        self._db.collection("follows").truncate()
        self._db.collection("persons").truncate()

    def create_indexes(self) -> None:
        self._db.collection("persons").add_persistent_index(fields=[self.indexed_property])

    def load_nodes(self, nodes: Iterable[NodeRecord], batch_size: int) -> int:
        col = self._db.collection("persons")
        batch: list[dict] = []
        total = 0
        for n in nodes:
            batch.append({"_key": n.node_id, "handle": n.props.get("handle", n.node_id)})
            if len(batch) >= batch_size:
                col.insert_many(batch, overwrite=True)
                total += len(batch)
                batch = []
        if batch:
            col.insert_many(batch, overwrite=True)
            total += len(batch)
        return total

    def load_edges(self, edges: Iterable[EdgeRecord], batch_size: int) -> int:
        col = self._db.collection("follows")
        batch: list[dict] = []
        total = 0
        for e in edges:
            batch.append({"_from": f"persons/{e.src_id}", "_to": f"persons/{e.dst_id}"})
            if len(batch) >= batch_size:
                col.insert_many(batch, overwrite=True)
                total += len(batch)
                batch = []
        if batch:
            col.insert_many(batch, overwrite=True)
            total += len(batch)
        return total

    def traversal(self, start_id: str, hops: int) -> float:
        aql = (
            "FOR v IN @hops..@hops OUTBOUND @start GRAPH @g "
            "COLLECT WITH COUNT INTO c RETURN c"
        )
        t0 = time.perf_counter()
        cursor = self._db.aql.execute(
            aql, bind_vars={"start": f"persons/{start_id}", "hops": hops, "g": self.GRAPH_NAME}
        )
        list(cursor)
        return (time.perf_counter() - t0) * 1000

    def point_lookup(self, node_id: str) -> float:
        t0 = time.perf_counter()
        self._db.collection("persons").get(node_id)
        return (time.perf_counter() - t0) * 1000

    def indexed_lookup(self, value: str) -> float:
        aql = f"FOR p IN persons FILTER p.{self.indexed_property} == @v RETURN p"
        t0 = time.perf_counter()
        list(self._db.aql.execute(aql, bind_vars={"v": value}))
        return (time.perf_counter() - t0) * 1000

    def aggregation(self) -> float:
        aql = (
            "FOR e IN follows COLLECT src = e._from WITH COUNT INTO out_degree "
            "SORT out_degree DESC LIMIT 100 RETURN {src, out_degree}"
        )
        t0 = time.perf_counter()
        list(self._db.aql.execute(aql))
        return (time.perf_counter() - t0) * 1000

    def mixed_op(self, is_read: bool) -> float:
        t0 = time.perf_counter()
        if is_read:
            rid = str(random.randint(0, 1_000_000))
            self._db.collection("persons").get(rid)
        else:
            rid = f"mixed-{random.randint(0, 10_000_000)}"
            self._db.collection("persons").insert(
                {"_key": rid, "handle": rid, "mixed": True}, overwrite=True
            )
        return (time.perf_counter() - t0) * 1000

    def footprint(self) -> dict:
        try:
            stats = self._db.collection("persons").statistics()
            return {
                "node_count": self._db.collection("persons").count(),
                "rel_count": self._db.collection("follows").count(),
                "figures": stats.get("figures", "not observable"),
            }
        except Exception as exc:
            return {"error": str(exc), "note": "stats() unavailable on this deployment"}
