from benchmark.metrics.stats import summarize


def test_summarize_basic():
    s = summarize([10, 20, 30, 40, 50])
    assert s.count == 5
    assert s.min_ms == 10
    assert s.max_ms == 50
    assert s.p50_ms == 30


def test_summarize_empty():
    s = summarize([])
    assert s.count == 0
    assert s.p50_ms == 0.0


def test_summarize_single_value():
    s = summarize([42.0])
    assert s.p50_ms == s.p95_ms == s.p99_ms == 42.0
