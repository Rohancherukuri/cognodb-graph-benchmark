from __future__ import annotations

import pytest

from benchmark.adapters.surrealdb_adapter import SurrealDBAdapter

from ..conftest import requires_env


def test_defaults_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "SURREALDB_URL",
        "SURREALDB_USER",
        "SURREALDB_PASSWORD",
        "SURREALDB_NAMESPACE",
        "SURREALDB_DATABASE",
    ):
        monkeypatch.delenv(var, raising=False)

    adapter = SurrealDBAdapter()

    assert adapter.url == "ws://localhost:8000"
    assert adapter.user == "root"
    assert adapter.password == "root"
    assert adapter.namespace == "benchmark"
    assert adapter.database == "benchmark"


def test_reads_custom_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SURREALDB_URL", "wss://example.surreal.cloud")
    monkeypatch.setenv("SURREALDB_USER", "bench_user")
    monkeypatch.setenv("SURREALDB_PASSWORD", "s3cr3t")
    monkeypatch.setenv("SURREALDB_NAMESPACE", "myns")
    monkeypatch.setenv("SURREALDB_DATABASE", "mydb")

    adapter = SurrealDBAdapter()

    assert adapter.url == "wss://example.surreal.cloud"
    assert adapter.user == "bench_user"
    assert adapter.password == "s3cr3t"
    assert adapter.namespace == "myns"
    assert adapter.database == "mydb"


def test_cloud_url_with_rpc_suffix_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    cloud_url = (
        "wss://testing-06aqpjfb9tqqp4693apn2mrdcg.aws-use1."
        "surreal.cloud/rpc"
    )

    monkeypatch.setenv(
        "SURREALDB_URL",
        cloud_url,
    )

    adapter = SurrealDBAdapter()

    assert adapter.url == cloud_url


def test_close_before_connect_does_not_raise() -> None:
    adapter = SurrealDBAdapter()
    adapter.close()  # must be a no-op, not an AttributeError on self._db


def test_use_before_connect_raises_runtime_error() -> None:
    adapter = SurrealDBAdapter()
    with pytest.raises(RuntimeError):
        adapter.point_lookup("0")


@pytest.mark.live
@requires_env("SURREALDB_URL")
def test_connect_and_close_against_real_surrealdb() -> None:
    """Requires a real SurrealDB instance reachable at SURREALDB_URL - e.g.
    `make infra-up` for the docker-compose service, or a SurrealDB Cloud
    instance. Opens a real connection, runs a trivial query to prove the
    session actually works, and tears it down. Skipped by default; run
    with `pytest -m live`.
    """
    adapter = SurrealDBAdapter()
    try:
        adapter.connect()
        adapter._require_db().query("RETURN 1;")
    finally:
        adapter.close()