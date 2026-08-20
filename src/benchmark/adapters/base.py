"""Common interface every graph-database adapter must implement.

Keeping this interface small and identical across platforms is what makes
the benchmark fair: the orchestrator only ever talks to this contract, never
to a platform-specific driver, so every platform is exercised through
exactly the same sequence of operations (assignment section 5.3, "same
logical queries ... for every platform").
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class NodeRecord:
    node_id: str
    label: str
    props: dict = field(default_factory=dict)


@dataclass
class EdgeRecord:
    src_id: str
    dst_id: str
    rel_type: str
    props: dict = field(default_factory=dict)


class GraphDBAdapter(abc.ABC):
    """One adapter instance == one platform under test."""

    name: str = "base"
    indexed_property: str = "handle"

    # -- lifecycle ------------------------------------------------------
    @abc.abstractmethod
    def connect(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def clear(self) -> None:
        """Wipe all data so every run starts from an identical empty state."""

    @abc.abstractmethod
    def create_indexes(self) -> None:
        """Create whatever index the platform needs for the indexed-lookup
        workload. Must set/keep `self.indexed_property` in sync with what
        was actually indexed, since the README table reports it verbatim.
        """

    # -- loading ----------------------------------------------------------
    @abc.abstractmethod
    def load_nodes(self, nodes: Iterable[NodeRecord], batch_size: int) -> int: ...

    @abc.abstractmethod
    def load_edges(self, edges: Iterable[EdgeRecord], batch_size: int) -> int: ...

    # -- single-operation primitives (each returns latency in milliseconds) --
    @abc.abstractmethod
    def traversal(self, start_id: str, hops: int) -> float: ...

    @abc.abstractmethod
    def point_lookup(self, node_id: str) -> float: ...

    @abc.abstractmethod
    def indexed_lookup(self, value: str) -> float: ...

    @abc.abstractmethod
    def aggregation(self) -> float: ...

    @abc.abstractmethod
    def mixed_op(self, is_read: bool) -> float:
        """A single operation for the mixed read/write workload. Callers
        pick `is_read` according to the configured read/write ratio and
        fire many of these concurrently from a thread pool.
        """

    # -- footprint ----------------------------------------------------------
    @abc.abstractmethod
    def footprint(self) -> dict:
        """Whatever the platform exposes about stored size / memory. Return
        {"note": "not observable"} (or similar) rather than guessing -
        section 5.2 explicitly asks for honesty here over fabricated numbers.
        """
