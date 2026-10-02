import pytest
from backend.app.analysis.anomaly import AnomalyEngine
from backend.app.schemas.metrics import MetricPercentileStats


def test_detect_anomalies_dns_failure():
    engine = AnomalyEngine()
    dns_res = {"status": "DNS_FAILURE", "latency_ms": 50.0, "error_message": "NXDOMAIN"}
    anomalies = engine.detect_anomalies(
        dns_res=dns_res,
        tcp_res=None,
        tls_res=None,
        http_res=None,
        network_hops=[],
        system_metric=None,
        baselines={},
    )
    assert len(anomalies) == 1
    assert anomalies[0].rule_triggered == "DNS_RESOLUTION_FAILURE"
    assert anomalies[0].severity == "CRITICAL"


def test_detect_anomalies_baseline_exceeded_with_sufficient_samples():
    engine = AnomalyEngine()
    # Baseline with 20 samples, P95 = 200ms
    bl = MetricPercentileStats(
        metric_name="http_latency_ms",
        count=20,
        min=50.0,
        max=220.0,
        mean=100.0,
        median=95.0,
        p50=95.0,
        p95=200.0,
        p99=215.0,
        std_dev=25.0,
        is_sufficient_evidence=True,
    )
    http_res = {
        "status": "SUCCESS",
        "status_code": 200,
        "ttfb_ms": 800.0,
        "total_latency_ms": 850.0,  # Far above P95 of 200ms
    }
    anomalies = engine.detect_anomalies(
        dns_res=None,
        tcp_res=None,
        tls_res=None,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
        baselines={"http_latency_ms": bl},
    )
    assert any(a.rule_triggered == "HTTP_BASELINE_P95_EXCEEDED" for a in anomalies)


def test_detect_anomalies_suppresses_baseline_when_insufficient_samples():
    engine = AnomalyEngine()
    # Baseline with only 4 samples (< 10)
    bl = MetricPercentileStats(
        metric_name="http_latency_ms",
        count=4,
        min=50.0,
        max=120.0,
        mean=100.0,
        median=95.0,
        p50=95.0,
        p95=115.0,
        p99=120.0,
        std_dev=20.0,
        is_sufficient_evidence=False,  # Insufficient!
    )
    http_res = {
        "status": "SUCCESS",
        "status_code": 200,
        "ttfb_ms": 130.0,
        "total_latency_ms": 150.0,
    }
    anomalies = engine.detect_anomalies(
        dns_res=None,
        tcp_res=None,
        tls_res=None,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
        baselines={"http_latency_ms": bl},
    )
    # Must NOT flag HTTP_BASELINE_P95_EXCEEDED due to insufficient samples safeguard
    assert not any(a.rule_triggered == "HTTP_BASELINE_P95_EXCEEDED" for a in anomalies)
