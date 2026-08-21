from __future__ import annotations

import os
import random
import time
from dotenv import load_dotenv
from typing import Any, Iterable, Optional, Protocol

from surrealdb import RecordID, Surreal

from .base import EdgeRecord, GraphDBAdapter, NodeRecord

load_dotenv()  # for local development convenience; CI/CD should set env vars directly

class _SurrealConnection(Protocol):
    """The subset of the `surrealdb` client's blocking-connection interface
    this adapter relies on. `Surreal(url)` returns one of several concrete
    connection classes (ws/http/embedded) depending on the URL scheme; this
    Protocol lets the adapter type-check against behavior rather than one
    specific class.
    """

    def signin(self, vars: dict[str, Any]) -> Any: ...
    def use(self, namespace: str, database: str) -> None: ...
    def query(self, query: str, vars: Optional[dict[str, Any]] = None) -> Any: ...
    def select(self, record: Any) -> Any: ...
    def close(self) -> None: ...


class SurrealDBAdapter(GraphDBAdapter):
    """SurrealDB, self-hosted via docker-compose and capped to the same
    vCPU/RAM as CognoDB's free tier. Models "follows" as a native SurrealDB
    graph edge table (`RELATE person->follows->person`) and traverses it
    with SurrealQL's `->edge->table` graph-traversal syntax.

    Verified against the official `surrealdb` PyPI package (v2.0.0)'s
    synchronous client:
      - `Surreal(url)` is a factory that picks a ws/http/embedded connection
        based on the URL scheme. Pass the base URL WITHOUT a trailing
        `/rpc` - the driver appends that itself.
      - `signin()` takes `{"username": ..., "password": ...}` (not
        `user`/`pass`).
      - `.query()` only surfaces the error status of the FIRST statement in
        a semicolon-separated string, so DDL here is issued as separate
        calls rather than one bundled multi-statement string, to avoid a
        later statement's failure going unnoticed.

    Env vars: SURREALDB_URL (default ws://localhost:8000), SURREALDB_USER,
    SURREALDB_PASSWORD, SURREALDB_NAMESPACE, SURREALDB_DATABASE.
    """

    name = "surrealdb"
    indexed_property = "handle"
    TABLE = "person"
    EDGE_TABLE = "follows"

    def __init__(self) -> None:
        self.url: str = os.environ.get("SURREALDB_URL", "ws://localhost:8000")
        self.user: str = os.environ.get("SURREALDB_USER", "root")
        self.password: str = os.environ.get("SURREALDB_PASSWORD", "root")
        self.namespace: str = os.environ.get("SURREALDB_NAMESPACE", "benchmark")
        self.database: str = os.environ.get("SURREALDB_DATABASE", "benchmark")
        self._db: Optional[_SurrealConnection] = None
        self.auth_level = os.environ.get("SURREALDB_AUTH_LEVEL", "root").lower()  # SurrealDB Cloud only
        self._loaded_node_ids: list[str] = []
    
    def _signin(self) -> None:
        """Authenticate with SurrealDB based on the configured auth level."""

        if self._db is None:
            raise RuntimeError("SurrealDB connection has not been initialized.")

        if self.auth_level == "root":
            self._db.signin(
                {
                    "username": self.user,
                    "password": self.password,
                }
            )

        elif self.auth_level == "namespace":
            self._db.signin(
                {
                    "namespace": self.namespace,
                    "username": self.user,
                    "password": self.password,
                }
            )

        elif self.auth_level == "database":
            self._db.signin(
                {
                    "namespace": self.namespace,
                    "database": self.database,
                    "username": self.user,
                    "password": self.password,
                }
            )

        else:
            raise ValueError(
                "Unsupported SURREALDB_AUTH_LEVEL: "
                f"{self.auth_level!r}. "
                "Expected one of: root, namespace, database."
            )

    def connect(self) -> None:
        """Connect and authenticate with SurrealDB."""
        self._db = Surreal(self.url)

        try:
            self._signin()
            self._db.use(
                self.namespace,
                self.database,
            )

        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Close the SurrealDB connection."""

        if self._db is not None:
            try:
                self._db.close()
            finally:
                self._db = None

    def clear(self) -> None:
        db = self._require_db()

        db.query(
            f"DELETE {self.EDGE_TABLE};"
        )

        db.query(
            f"DELETE {self.TABLE};"
        )

        self._loaded_node_ids = []

    def create_indexes(self) -> None:
        db = self._require_db()
        # One statement per call - see class docstring on why these aren't
        # bundled into a single semicolon-separated string.
        db.query(f"DEFINE TABLE IF NOT EXISTS {self.TABLE} SCHEMALESS;")
        db.query(
            f"DEFINE TABLE IF NOT EXISTS {self.EDGE_TABLE} SCHEMALESS "
            f"TYPE RELATION FROM {self.TABLE} TO {self.TABLE};"
        )
        db.query(
            f"DEFINE INDEX IF NOT EXISTS {self.TABLE}_{self.indexed_property} "
            f"ON TABLE {self.TABLE} COLUMNS {self.indexed_property};"
        )

    def load_nodes(
            self,
            nodes: Iterable[NodeRecord],
            batch_size: int,
        ) -> int:
        batch: list[dict[str, Any]] = []
        total = 0

        # Reset node tracking for each new dataset load.
        self._loaded_node_ids = []

        for node in nodes:
            node_id = str(node.node_id)

            self._loaded_node_ids.append(node_id)

            batch.append(
                {
                    "id": node_id,
                    "handle": node.props.get(
                        "handle",
                        node_id,
                    ),
                }
            )

            if len(batch) >= batch_size:
                total += self._flush_nodes(batch)
                batch = []

        if batch:
            total += self._flush_nodes(batch)

        return total

    def _flush_nodes(self, batch: list[dict[str, Any]]) -> int:
        db = self._require_db()
        # `FOR ... IN ... { }` is a single top-level statement, so this
        # batch's success/failure IS correctly surfaced by `.query()`.
        query = (
            f"FOR $row IN $rows {{ "
            f"UPSERT type::thing('{self.TABLE}', $row.id) "
            f"CONTENT {{ "
            f"id: $row.id, "
            f"handle: $row.handle "
            f"}}; "
            f"}};"
        )
        db.query(query, {"rows": batch})
        return len(batch)

    def load_edges(self, edges: Iterable[EdgeRecord], batch_size: int) -> int:
        batch: list[dict[str, Any]] = []
        total = 0
        for e in edges:
            batch.append({"src": e.src_id, "dst": e.dst_id})
            if len(batch) >= batch_size:
                total += self._flush_edges(batch)
                batch = []
        if batch:
            total += self._flush_edges(batch)
        return total

    def _flush_edges(self, batch: list[dict[str, Any]]) -> int:
        db = self._require_db()
        query = (
            f"FOR $row IN $rows {{ "
            f"RELATE (type::thing('{self.TABLE}', $row.src))"
            f"->{self.EDGE_TABLE}->"
            f"(type::thing('{self.TABLE}', $row.dst)); "
            f"}};"
        )
        db.query(query, {"rows": batch})
        return len(batch)

    def traversal(self, start_id: str, hops: int) -> float:
        db = self._require_db()
        chain = f"->{self.EDGE_TABLE}->{self.TABLE}" * hops
        query = f"SELECT count() FROM $start{chain} GROUP ALL;"
        t0 = time.perf_counter()
        db.query(query, {"start": RecordID(self.TABLE, start_id)})
        return (time.perf_counter() - t0) * 1000

    def point_lookup(self, node_id: str) -> float:
        db = self._require_db()
        t0 = time.perf_counter()
        db.select(RecordID(self.TABLE, node_id))
        return (time.perf_counter() - t0) * 1000

    def indexed_lookup(self, value: str) -> float:
        db = self._require_db()
        query = f"SELECT * FROM {self.TABLE} WHERE {self.indexed_property} = $v;"
        t0 = time.perf_counter()
        db.query(query, {"v": value})
        return (time.perf_counter() - t0) * 1000

    def aggregation(self) -> float:
        db = self._require_db()
        query = (
            f"SELECT id, count(->{self.EDGE_TABLE}->{self.TABLE}) AS out_degree "
            f"FROM {self.TABLE} ORDER BY out_degree DESC LIMIT 100;"
        )
        t0 = time.perf_counter()
        db.query(query)
        return (time.perf_counter() - t0) * 1000

    def mixed_op(self, is_read: bool) -> float:
        db = self._require_db()

        if not self._loaded_node_ids:
            raise RuntimeError(
                "No benchmark nodes are available for the mixed workload."
            )

        node_id = random.choice(
            self._loaded_node_ids
        )

        t0 = time.perf_counter()

        if is_read:
            db.select(
                RecordID(
                    self.TABLE,
                    node_id,
                )
            )

        else:
            db.query(
                f"UPDATE type::thing('{self.TABLE}', $id) "
                f"SET mixed = true;",
                {
                    "id": node_id,
                },
            )

        return (
            time.perf_counter() - t0
        ) * 1000

    def footprint(self) -> dict[str, Any]:
        db = self._require_db()
        try:
            person_count = db.query(f"SELECT count() FROM {self.TABLE} GROUP ALL;")
            follows_count = db.query(f"SELECT count() FROM {self.EDGE_TABLE} GROUP ALL;")
            return {
                "node_count": _first_count(person_count),
                "rel_count": _first_count(follows_count),
                "note": "stored-data size (bytes) is not exposed via SurrealQL on this deployment.",
            }
        except Exception as exc:  # noqa: BLE001 - footprint is best-effort by design
            return {"error": str(exc)}

    def _require_db(self) -> _SurrealConnection:
        if self._db is None:
            raise RuntimeError("SurrealDBAdapter.connect() must be called before use")
        return self._db


def _first_count(result: Any) -> Optional[int]:
    """`SELECT count() ... GROUP ALL` returns a single-row result shaped
    like `[{"count": N}]`. Normalized defensively since the exact wrapper
    shape has shifted between SurrealDB server/client versions before.
    """
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0].get("count")
    return None