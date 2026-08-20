from __future__ import annotations

from pathlib import Path


def read_epinions_edges(
    path: Path,
) -> list[tuple[int, int]]:
    """
    Read directed relationships from the SNAP Epinions dataset.

    Expected format:

        # comment
        # comment
        source_id target_id
        source_id target_id

    Lines beginning with '#' and empty lines are ignored.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Epinions dataset not found: {path}"
        )

    edges: list[tuple[int, int]] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, raw_line in enumerate(
            file,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) != 2:
                raise ValueError(
                    "Invalid edge format at "
                    f"line {line_number}: {line!r}"
                )

            try:
                source_id = int(parts[0])
                target_id = int(parts[1])

            except ValueError as exc:
                raise ValueError(
                    "Invalid node ID at "
                    f"line {line_number}: {line!r}"
                ) from exc

            edges.append(
                (source_id, target_id)
            )

    if not edges:
        raise ValueError(
            "No relationships were found "
            "in the Epinions dataset."
        )

    return edges