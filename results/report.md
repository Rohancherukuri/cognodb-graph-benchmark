# Graph Database Benchmark Report

## 1. Executive Summary

This report compares five graph-capable database platforms using a benchmark based on the SNAP `soc-Epinions1` social network dataset.

The platforms evaluated are:

- CognoDB
- Neo4j Aura
- Memgraph
- ArangoDB
- SurrealDB

The benchmark evaluates several important aspects of graph database performance:

1. Data ingestion performance
2. Graph traversal performance
3. Point lookup performance
4. Indexed property lookup performance
5. Aggregation performance
6. Mixed read/write workload performance
7. Dataset footprint
8. Overall suitability for graph workloads

The benchmark dataset contains approximately **35,854 nodes** and **100,000 relationships**, sampled deterministically from the original SNAP Epinions dataset containing **508,837 relationships**.

Based on the estimated benchmark results:

- **Memgraph** is expected to provide the strongest overall low-latency graph performance.
- **CognoDB** is expected to perform competitively for Cypher/Bolt-based graph workloads.
- **Neo4j Aura** provides strong graph capabilities but cloud/network overhead can affect benchmark latency.
- **ArangoDB** offers flexibility through its multi-model architecture but may not be the fastest option for pure graph workloads.
- **SurrealDB** provides a flexible modern database architecture but WebSocket/RPC overhead can significantly affect small-query latency.

The results should be treated as **estimated projections** until the complete benchmark is successfully executed against all platforms under identical infrastructure conditions.

---

# 2. Benchmark Objective

The objective of this benchmark is to evaluate how different graph database platforms perform when executing common graph workloads.

The benchmark focuses on realistic operations that are commonly required by graph-based applications:

- Creating graph nodes
- Creating graph relationships
- Traversing one-hop relationships
- Traversing multi-hop relationships
- Looking up nodes by identifier
- Looking up indexed properties
- Performing aggregation queries
- Executing mixed read/write workloads

The benchmark is designed to provide a common abstraction layer through database adapters so that each platform can be evaluated using the same dataset and workload definitions.

---

# 3. Dataset

## Dataset Source

The benchmark uses the:

```text
SNAP soc-Epinions1 dataset