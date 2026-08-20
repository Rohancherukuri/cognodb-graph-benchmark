from __future__ import annotations

import csv
import random
from pathlib import Path

import networkx as nx


def generate_synthetic(
    target_edges: int,
    out_dir: Path,
    seed: int = 42,
) -> dict:
    """
    Generate a deterministic synthetic graph containing
    exactly target_edges relationships.

    This is intended for offline development and testing.
    """

    if target_edges <= 0:
        raise ValueError(
            "target_edges must be greater than zero."
        )

    rng = random.Random(seed)

    n_nodes = max(
        1_000,
        target_edges // 3,
    )

    graph = nx.barabasi_albert_graph(
        n=n_nodes,
        m=3,
        seed=seed,
    )

    directed_edges: list[
        tuple[int, int]
    ] = []

    for source_id, target_id in graph.edges():

        directed_edges.append(
            (source_id, target_id)
        )

        if rng.random() < 0.30:

            directed_edges.append(
                (target_id, source_id)
            )

    while len(directed_edges) < target_edges:

        source_id = rng.randrange(
            n_nodes
        )

        target_id = rng.randrange(
            n_nodes
        )

        if source_id != target_id:

            directed_edges.append(
                (
                    source_id,
                    target_id,
                )
            )

    rng.shuffle(
        directed_edges
    )

    selected_edges = directed_edges[
        :target_edges
    ]

    nodes = sorted(
        {
            node_id
            for source_id, target_id
            in selected_edges
            for node_id in (
                source_id,
                target_id,
            )
        }
    )

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes_path = (
        out_dir
        / "nodes.csv"
    )

    edges_path = (
        out_dir
        / "edges.csv"
    )

    with nodes_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            ["node_id"]
        )

        for node_id in nodes:

            writer.writerow(
                [node_id]
            )

    with edges_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "source_id",
                "target_id",
                "relationship_type",
            ]
        )

        for source_id, target_id in selected_edges:

            writer.writerow(
                [
                    source_id,
                    target_id,
                    "RELATED_TO",
                ]
            )

    return {
        "source": (
            "synthetic "
            "(NetworkX Barabasi-Albert graph)"
        ),
        "node_count": len(nodes),
        "relationship_count": len(
            selected_edges
        ),
        "relationship_type": "RELATED_TO",
        "seed": seed,
    }