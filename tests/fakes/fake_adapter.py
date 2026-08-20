from __future__ import annotations

import random
import time

from benchmark.adapters.base import EdgeRecord, GraphDBAdapter, NodeRecord


class FakeAdapter(GraphDBAdapter):
    """In-memory adapter used only by the test suite, so the orchestration
    logic (batching, percentile math, mixed-workload concurrency, report
    generation) can be verified without any live database. The real
    platforms are exercised through the real adapters, which need live
    credentials and are deliberately NOT part of the unit-test suite (they
    belong to a manual/CI-optional "live benchmark" run instead).
    """

    name = "fake"
    indexed_property = "handle"

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, list[str]] = {}

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()

    def create_indexes(self) -> None:
        pass

    def load_nodes(self, nodes, batch_size: int) -> int:
        n = 0
        for rec in nodes:
            self.nodes[rec.node_id] = rec.props
            n += 1
        return n

    def load_edges(self, edges, batch_size: int) -> int:
        n = 0
        for rec in edges:
            self.edges.setdefault(rec.src_id, []).append(rec.dst_id)
            n += 1
        return n

    @staticmethod
    def _fake_latency() -> float:
        return random.uniform(0.1, 2.0)

    def traversal(self, start_id: str, hops: int) -> float:
        return self._fake_latency()

    def point_lookup(self, node_id: str) -> float:
        return self._fake_latency()

    def indexed_lookup(self, value: str) -> float:
        return self._fake_latency()

    def aggregation(self) -> float:
        return self._fake_latency()

    def mixed_op(self, is_read: bool) -> float:
        return self._fake_latency()

    def footprint(self) -> dict:
        return {
            "node_count": len(self.nodes),
            "rel_count": sum(len(v) for v in self.edges.values()),
        }
