from pathlib import Path

from benchmark.dataset.prepare import prepare_dataset


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    raw_path = (
        project_root
        / "data"
        / "raw"
        / "soc-Epinions1.txt"
    )

    output_dir = (
        project_root
        / "data"
        / "processed"
        / "epinions_100k"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Preparing Epinions dataset...")
    print(f"Raw dataset: {raw_path}")
    print(f"Output directory: {output_dir}")

    result = prepare_dataset(
        raw_path=raw_path,
        output_dir=output_dir,
        edge_limit=100_000,
        seed=42,
    )

    print("\nDataset preparation complete.")

    print(f"Nodes: {result['node_count']}")
    print(f"Relationships: {result['edge_count']}")

    print("\nGenerated files:")

    for name, path in result["files"].items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()