import pytest
from backend.app.analysis.baseline import BaselineEngine


def test_baseline_insufficient_samples_flag():
    engine = BaselineEngine(min_samples=10)
    # Fewer than 10 samples
    samples = [100.0, 110.0, 105.0, 95.0, 120.0]
    stats = engine.calculate_stats(samples, "http_latency_ms")

    assert stats.count == 5
    assert stats.is_sufficient_evidence is False
    assert stats.min == 95.0
    assert stats.max == 120.0
    assert stats.median == 105.0


def test_baseline_sufficient_samples_and_percentiles():
    engine = BaselineEngine(min_samples=10)
    # 20 samples from 10 to 200
    samples = [float(i * 10) for i in range(1, 21)]
    stats = engine.calculate_stats(samples, "http_latency_ms")

    assert stats.count == 20
    assert stats.is_sufficient_evidence is True
    assert stats.min == 10.0
    assert stats.max == 200.0
    assert stats.p50 == pytest.approx(105.0, abs=1.0)
    assert stats.p95 == pytest.approx(190.5, abs=2.0)
    assert stats.p99 == pytest.approx(198.1, abs=2.0)
    assert stats.mean == 105.0
    assert stats.std_dev > 0.0


def test_baseline_empty_samples():
    engine = BaselineEngine(min_samples=10)
    stats = engine.calculate_stats([], "dns_latency_ms")
    assert stats.count == 0
    assert stats.is_sufficient_evidence is False
    assert stats.p50 == 0.0
