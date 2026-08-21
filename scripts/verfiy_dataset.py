import csv
from pathlib import Path


def count_rows(path: Path) -> int:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.reader(file)

        next(reader, None)

        return sum(1 for _ in reader)


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    dataset_dir = (
        project_root
        / "data"
        / "processed"
        / "epinions_100k"
    )

    nodes_path = dataset_dir / "nodes.csv"
    edges_path = dataset_dir / "edges.csv"

    if not nodes_path.exists():
        raise FileNotFoundError(
            f"Missing nodes file: {nodes_path}"
        )

    if not edges_path.exists():
        raise FileNotFoundError(
            f"Missing edges file: {edges_path}"
        )

    node_count = count_rows(nodes_path)
    edge_count = count_rows(edges_path)

    print("\nDataset verification")
    print("=" * 40)

    print(f"Nodes: {node_count:,}")
    print(f"Relationships: {edge_count:,}")

    if edge_count != 100_000:
        raise ValueError(
            f"Expected 100,000 relationships, "
            f"but found {edge_count:,}"
        )

    print("\n✓ Dataset verification passed")


if __name__ == "__main__":
    main()