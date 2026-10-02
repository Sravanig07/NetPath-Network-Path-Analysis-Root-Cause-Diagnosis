import pytest
from datetime import datetime, timedelta
from backend.app.analysis.diagnosis import DiagnosisEngine
from backend.app.schemas.metrics import MetricPercentileStats


class MockDB:
    """Mock database session for isolation testing."""
    pass


def test_scenario_1_http_application_latency():
    """
    Scenario 1:
    DNS, TCP, TLS are nominal.
    HTTP latency = 1,820ms, historical P95 = 240ms.
    Must diagnose HTTP_APPLICATION_LATENCY with Evidence Score >= 6.
    """
    engine = DiagnosisEngine()

    # Pre-populate historical baseline for http_latency_ms
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {
        "http_latency_ms": MetricPercentileStats(
            metric_name="http_latency_ms",
            count=25,
            min=90.0,
            max=300.0,
            mean=130.0,
            median=120.0,
            p50=120.0,
            p95=240.0,
            p99=280.0,
            std_dev=30.0,
            is_sufficient_evidence=True,
        )
    }

    dns_res = {"status": "SUCCESS", "latency_ms": 18.0, "addresses": ["93.184.216.34"]}
    tcp_res = {"status": "SUCCESS", "destination_ip": "93.184.216.34", "destination_port": 443, "connect_latency_ms": 22.0}
    tls_res = {"status": "SUCCESS", "handshake_latency_ms": 35.0, "is_valid": True}
    http_res = {
        "status": "HTTP_APPLICATION_LATENCY",
        "status_code": 200,
        "ttfb_ms": 1780.0,
        "total_latency_ms": 1820.0,
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=tls_res,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
    )

    diag = result["diagnosis"]
    assert diag.category == "HTTP_APPLICATION_LATENCY"
    assert diag.affected_layer == "HTTP"
    assert diag.severity == "HIGH"
    assert diag.evidence_score >= 6
    assert len(diag.recommendations) > 0


def test_scenario_2_http_server_error_500():
    """
    Scenario 2:
    DNS, TCP, TLS are nominal.
    HTTP returns 500 Internal Server Error.
    Must diagnose HTTP_APPLICATION_ERROR with high severity.
    """
    engine = DiagnosisEngine()
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {}

    dns_res = {"status": "SUCCESS", "latency_ms": 15.0, "addresses": ["1.2.3.4"]}
    tcp_res = {"status": "SUCCESS", "destination_ip": "1.2.3.4", "destination_port": 80, "connect_latency_ms": 20.0}
    http_res = {
        "status": "HTTP_APPLICATION_ERROR",
        "status_code": 500,
        "error_message": "Internal Server Error",
        "ttfb_ms": 40.0,
        "total_latency_ms": 45.0,
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=None,
        http_res=http_res,
        network_hops=[],
        system_metric=None,
    )

    diag = result["diagnosis"]
    assert diag.category == "HTTP_APPLICATION_ERROR"
    assert diag.affected_layer == "HTTP"
    assert diag.severity == "CRITICAL"
    assert diag.evidence_score >= 5


def test_scenario_3_service_unavailable_tcp_refused():
    """
    Scenario 3:
    DNS resolves, but TCP connection is refused (daemon down).
    Must diagnose TCP_CONNECTIVITY_FAILURE and NOT blame HTTP.
    """
    engine = DiagnosisEngine()
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {}

    dns_res = {"status": "SUCCESS", "latency_ms": 12.0, "addresses": ["10.0.0.5"]}
    tcp_res = {
        "status": "TCP_CONNECTIVITY_FAILURE",
        "destination_ip": "10.0.0.5",
        "destination_port": 8080,
        "connect_latency_ms": 10.0,
        "error_message": "Connection refused on port 8080",
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=None,
        http_res=None,
        network_hops=[],
        system_metric=None,
    )

    diag = result["diagnosis"]
    assert diag.category == "TCP_CONNECTIVITY_FAILURE"
    assert diag.affected_layer == "TCP"
    assert diag.severity == "CRITICAL"


def test_scenario_4_dns_nxdomain_failure():
    """
    Scenario 4:
    DNS returns NXDOMAIN.
    Must diagnose DNS_FAILURE and suppress downstream layer blame.
    """
    engine = DiagnosisEngine()
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {}

    dns_res = {
        "status": "DNS_FAILURE",
        "latency_ms": 45.0,
        "error_message": "Domain does not exist (NXDOMAIN)",
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res=dns_res,
        tcp_res=None,
        tls_res=None,
        http_res=None,
        network_hops=[],
        system_metric=None,
    )

    diag = result["diagnosis"]
    assert diag.category == "DNS_FAILURE"
    assert diag.affected_layer == "DNS"
    assert diag.severity == "CRITICAL"


def test_scenario_5_tls_certificate_expiring():
    """
    Scenario 5:
    DNS and TCP are normal.
    TLS certificate expires in 8 days (< 30 days threshold).
    Must diagnose TLS_CERTIFICATE_EXPIRING.
    """
    engine = DiagnosisEngine()
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {}

    dns_res = {"status": "SUCCESS", "latency_ms": 14.0, "addresses": ["1.1.1.1"]}
    tcp_res = {"status": "SUCCESS", "destination_ip": "1.1.1.1", "destination_port": 443, "connect_latency_ms": 18.0}
    exp_date = datetime.utcnow() + timedelta(days=8)
    tls_res = {
        "status": "TLS_CERTIFICATE_EXPIRING",
        "handshake_latency_ms": 28.0,
        "days_to_expiration": 8,
        "cert_expires_at": exp_date,
        "is_valid": True,
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res=dns_res,
        tcp_res=tcp_res,
        tls_res=tls_res,
        http_res=None,
        network_hops=[],
        system_metric=None,
    )

    diag = result["diagnosis"]
    assert diag.category == "TLS_CERTIFICATE_EXPIRING"
    assert diag.affected_layer == "TLS"
    assert diag.severity == "HIGH"


def test_scenario_6_resource_pressure():
    """
    Scenario 6:
    Local host CPU utilization at 95%.
    Must detect RESOURCE_PRESSURE anomaly and flag host exhaustion.
    """
    engine = DiagnosisEngine()
    engine.baseline_engine.get_target_baselines = lambda db, target_id: {}

    sys_metric = {
        "status": "RESOURCE_PRESSURE",
        "cpu_pct": 95.2,
        "memory_pct": 88.0,
        "load_1m": 4.5,
        "error_message": "Host resource exhaustion: CPU=95.2%, Mem=88.0%",
    }

    result = engine.diagnose(
        db=MockDB(),
        target_id=1,
        dns_res={"status": "SUCCESS", "latency_ms": 10.0},
        tcp_res={"status": "SUCCESS", "connect_latency_ms": 15.0},
        tls_res=None,
        http_res={"status": "SUCCESS", "status_code": 200, "total_latency_ms": 120.0},
        network_hops=[],
        system_metric=sys_metric,
    )

    diag = result["diagnosis"]
    assert diag.category == "RESOURCE_PRESSURE"
    assert diag.affected_layer == "System"
