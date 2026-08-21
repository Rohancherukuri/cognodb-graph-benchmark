def run_platform(
    platform_name: str,
    nodes_path: Path,
    edges_path: Path,
) -> dict[str, dict[str, float]]:
    adapter = get_adapter(platform_name)

    try:
        adapter.connect()

        adapter.clear_benchmark_data()

        ingest_result = run_ingestion(
            adapter=adapter,
            nodes_path=nodes_path,
            edges_path=edges_path,
        )

        traversal_result = run_traversal_benchmark(
            adapter=adapter,
        )

        lookup_result = run_lookup_benchmark(
            adapter=adapter,
        )

        aggregation_result = run_aggregation_benchmark(
            adapter=adapter,
        )

        footprint_result = run_footprint_benchmark(
            adapter=adapter,
        )

        return {
            "platform": platform_name,
            "ingest": ingest_result,
            "traversal": traversal_result,
            "lookup": lookup_result,
            "aggregation": aggregation_result,
            "footprint": footprint_result,
        }

    finally:
        try:
            adapter.clear_benchmark_data()
        finally:
            adapter.close()