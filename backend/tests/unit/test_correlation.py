import pytest
from backend.app.analysis.correlation import CorrelationEngine
from backend.app.schemas.analysis import AnomalySchema


def test_correlate_dns_failure_suppresses_blaming_tcp():
    engine = CorrelationEngine()
    dns_res = {"status": "DNS_FAILURE", "latency_ms": 30.0, "error_message": "Host not found"}
    anomalies = [
        AnomalySchema(
            metric_name="dns_resolution",
            observed_value=30.0,
            severity="CRITICAL",
            rule_triggered="DNS_RESOLUTION_FAILURE",
            evidence_text="DNS lookup returned NXDOMAIN",
        )
    ]
    category, severity, affected_layer, summary, evidence = engine.correlate(
        dns_res=dns_res,
        tcp_res=None,
        tls_res=None,
        http_res=None,
        network_hops=[],
        system_metric=None,
        anomalies=anomalies,
    )
    assert category == "DNS_FAILURE"
    assert affected_layer == "DNS"
    assert severity == "CRITICAL"
    assert any("blocked by DNS failure" in ev.description for ev in evidence)


def test_correlate_tcp_connectivity_failure():
    engine = CorrelationEngine()
    dns_res = {"status": "SUCCESS", "latency_ms": 15.0, "addresses": ["1.2.3.4"]}
    tcp_res = {
        "status": "TCP_CONNECTIVITY_FAILURE",
        "destination_ip": "1.2.3.4",
        "destination_port": 443,
        "connect_latency_ms": 5000.0,
        "error_message": "Connection refused",
    }
    anomalies = [
        AnomalySchema(
            metric_name="tcp_connect",
            observed_value=5000.0,
            severity="CRITICAL",
            rule_triggered="TCP_CONNECTIVITY_FAILURE",
            evidence_text="Connection refused",
        )
    ]
    category, severity, affected_layer, summary, evidence = engine.correlate(
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=None,
        http_res=None,
        network_hops=[],
        system_metric=None,
        anomalies=anomalies,
    )
    assert category == "TCP_CONNECTIVITY_FAILURE"
    assert affected_layer == "TCP"
    assert severity == "CRITICAL"


def test_correlate_http_application_latency():
    engine = CorrelationEngine()
    dns_res = {"status": "SUCCESS", "latency_ms": 12.0}
    tcp_res = {"status": "SUCCESS", "connect_latency_ms": 18.0}
    tls_res = {"status": "SUCCESS", "handshake_latency_ms": 25.0}
    http_res = {
        "status": "HTTP_APPLICATION_LATENCY",
        "status_code": 200,
        "ttfb_ms": 1850.0,
        "total_latency_ms": 1900.0,
    }
    anomalies = [
        AnomalySchema(
            metric_name="http_latency_ms",
            observed_value=1900.0,
            severity="HIGH",
            rule_triggered="HTTP_BASELINE_P95_EXCEEDED",
            evidence_text="HTTP latency exceeded P95",
        )
    ]
    category, severity, affected_layer, summary, evidence = engine.correlate(
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=tls_res,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
        anomalies=anomalies,
    )
    assert category == "HTTP_APPLICATION_LATENCY"
    assert affected_layer == "HTTP"
    assert severity == "HIGH"
    # Should highlight high TTFB in evidence
    assert any("TTFB was 1850.0ms" in ev.description for ev in evidence)


def test_correlate_http_server_error_500():
    engine = CorrelationEngine()
    dns_res = {"status": "SUCCESS", "latency_ms": 10.0}
    tcp_res = {"status": "SUCCESS", "connect_latency_ms": 15.0}
    tls_res = {"status": "SUCCESS", "handshake_latency_ms": 20.0}
    http_res = {
        "status": "HTTP_APPLICATION_ERROR",
        "status_code": 500,
        "error_message": "Internal Server Error",
    }
    anomalies = [
        AnomalySchema(
            metric_name="http_status_code",
            observed_value=500.0,
            severity="CRITICAL",
            rule_triggered="HTTP_SERVER_ERROR",
            evidence_text="Server returned HTTP 500",
        )
    ]
    category, severity, affected_layer, summary, evidence = engine.correlate(
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=tls_res,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
        anomalies=anomalies,
    )
    assert category == "HTTP_APPLICATION_ERROR"
    assert affected_layer == "HTTP"
    assert severity == "CRITICAL"
