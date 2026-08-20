from __future__ import annotations

import json
import os
import random
import time
from typing import Iterable, Optional
from dotenv import load_dotenv
import pydgraph
from .base import EdgeRecord, GraphDBAdapter, NodeRecord

load_dotenv()  # load env vars from .env file in project root


class DgraphAdapter(GraphDBAdapter):
    """Dgraph, self-hosted (dgraph/standalone) via docker-compose and capped
    to the same vCPU/RAM as CognoDB's free tier. Uses DQL over the gRPC
    Alpha endpoint, driven by the official `pydgraph` client.

    Env vars: DGRAPH_ALPHA_ADDR (default localhost:9080).
    """

    name = "dgraph"
    indexed_property = "handle"

    def __init__(self) -> None:
        self.addr = os.environ.get("DGRAPH_ALPHA_ADDR", "localhost:9080")
        self._stub = None
        self._client = None
        self._uid_cache: dict[str, str] = {}

    def connect(self) -> None:
        self._stub = pydgraph.DgraphClientStub(self.addr)
        self._client = pydgraph.DgraphClient(self._stub)

    def close(self) -> None:
        if self._stub:
            self._stub.close()

    def clear(self) -> None:
        self._client.alter(pydgraph.Operation(drop_all=True))
        self._uid_cache.clear()

    def create_indexes(self) -> None:
        schema = f"""
        external_id: string @index(exact) .
        {self.indexed_property}: string @index(exact) .
        follows: [uid] @reverse .
        """
        self._client.alter(pydgraph.Operation(schema=schema))

    def load_nodes(self, nodes: Iterable[NodeRecord], batch_size: int) -> int:
        batch: list[dict] = []
        total = 0
        for n in nodes:
            batch.append({"id": n.node_id, "handle": n.props.get("handle", n.node_id)})
            if len(batch) >= batch_size:
                total += self._flush_nodes(batch)
                batch = []
        if batch:
            total += self._flush_nodes(batch)
        return total

    def _flush_nodes(self, batch: list[dict]) -> int:
        txn = self._client.txn()
        try:
            mutations = [
                {"uid": f"_:{row['id']}", "external_id": row["id"], "handle": row["handle"]}
                for row in batch
            ]
            txn.mutate(set_obj=mutations, commit_now=True)
        finally:
            txn.discard()
        return len(batch)

    def _uid_for(self, external_id: str) -> Optional[str]:
        if external_id in self._uid_cache:
            return self._uid_cache[external_id]
        q = "query q($id: string) { q(func: eq(external_id, $id)) { uid } }"
        res = json.loads(
            self._client.txn(read_only=True).query(q, variables={"$id": external_id}).json
        )
        if res["q"]:
            uid = res["q"][0]["uid"]
            self._uid_cache[external_id] = uid
            return uid
        return None

    def load_edges(self, edges: Iterable[EdgeRecord], batch_size: int) -> int:
        batch: list[dict] = []
        total = 0
        for e in edges:
            src_uid, dst_uid = self._uid_for(e.src_id), self._uid_for(e.dst_id)
            if not (src_uid and dst_uid):
                continue
            batch.append({"uid": src_uid, "follows": [{"uid": dst_uid}]})
            if len(batch) >= batch_size:
                total += self._flush_edges(batch)
                batch = []
        if batch:
            total += self._flush_edges(batch)
        return total

    def _flush_edges(self, batch: list[dict]) -> int:
        txn = self._client.txn()
        try:
            txn.mutate(set_obj=batch, commit_now=True)
        finally:
            txn.discard()
        return len(batch)

    def traversal(self, start_id: str, hops: int) -> float:
        levels = "follows { " * hops + "uid" + " }" * hops
        q = "query q($id: string) { start(func: eq(external_id, $id)) { " + levels + " } }"
        t0 = time.perf_counter()
        self._client.txn(read_only=True).query(q, variables={"$id": start_id})
        return (time.perf_counter() - t0) * 1000

    def point_lookup(self, node_id: str) -> float:
        q = "query q($id: string) { q(func: eq(external_id, $id)) { uid external_id handle } }"
        t0 = time.perf_counter()
        self._client.txn(read_only=True).query(q, variables={"$id": node_id})
        return (time.perf_counter() - t0) * 1000

    def indexed_lookup(self, value: str) -> float:
        q = f"query q($v: string) {{ q(func: eq({self.indexed_property}, $v)) {{ uid }} }}"
        t0 = time.perf_counter()
        self._client.txn(read_only=True).query(q, variables={"$v": value})
        return (time.perf_counter() - t0) * 1000

    def aggregation(self) -> float:
        q = "{ q(func: has(follows)) { count(follows) } }"
        t0 = time.perf_counter()
        self._client.txn(read_only=True).query(q)
        return (time.perf_counter() - t0) * 1000

    def mixed_op(self, is_read: bool) -> float:
        t0 = time.perf_counter()
        if is_read:
            rid = str(random.randint(0, 1_000_000))
            q = "query q($id: string) { q(func: eq(external_id, $id)) { uid } }"
            self._client.txn(read_only=True).query(q, variables={"$id": rid})
        else:
            rid = f"mixed-{random.randint(0, 10_000_000)}"
            txn = self._client.txn()
            try:
                txn.mutate(
                    set_obj={"external_id": rid, "handle": rid, "mixed": True}, commit_now=True
                )
            finally:
                txn.discard()
        return (time.perf_counter() - t0) * 1000

    def footprint(self) -> dict:
        try:
            q = (
                "{ n(func: has(external_id)) { count(uid) } "
                "e(func: has(follows)) { c: count(follows) } }"
            )
            res = json.loads(self._client.txn(read_only=True).query(q).json)
            return {"raw": res, "note": "disk/memory size not exposed via the gRPC API"}
        except Exception as exc:
            return {"error": str(exc)}
