from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from backend.app.schemas.analysis import AnomalySchema
from backend.app.schemas.metrics import MetricPercentileStats

logger = logging.getLogger("netpath.analysis.anomaly")


class AnomalyEngine:
    """
    Deterministic anomaly detection combining threshold checks,
    historical baseline deviations (P95), and statistical Z-scores.
    """

    def detect_anomalies(
        self,
        dns_res: Optional[Dict[str, Any]],
        tcp_res: Optional[Dict[str, Any]],
        tls_res: Optional[Dict[str, Any]],
        http_res: Optional[Dict[str, Any]],
        network_hops: List[Dict[str, Any]],
        system_metric: Optional[Dict[str, Any]],
        baselines: Dict[str, MetricPercentileStats],
    ) -> List[AnomalySchema]:
        anomalies: List[AnomalySchema] = []

        # 1. DNS Anomalies
        if dns_res:
            if dns_res.get("status") == "DNS_FAILURE":
                anomalies.append(
                    AnomalySchema(
                        metric_name="dns_resolution",
                        observed_value=dns_res.get("latency_ms", 0.0),
                        expected_value=0.0,
                        baseline_reference="Status != SUCCESS",
                        severity="CRITICAL",
                        rule_triggered="DNS_RESOLUTION_FAILURE",
                        evidence_text=f"DNS resolution failed: {dns_res.get('error_message')}",
                    )
                )
            else:
                latency = dns_res.get("latency_ms", 0.0)
                bl = baselines.get("dns_latency_ms")
                if bl and bl.is_sufficient_evidence and latency > bl.p95:
                    anomalies.append(
                        AnomalySchema(
                            metric_name="dns_latency_ms",
                            observed_value=latency,
                            expected_value=bl.p50,
                            baseline_reference=f"P95: {bl.p95}ms (P50: {bl.p50}ms)",
                            severity="HIGH",
                            rule_triggered="DNS_BASELINE_P95_EXCEEDED",
                            evidence_text=f"DNS latency {latency:.1f}ms exceeds historical P95 ({bl.p95:.1f}ms)",
                        )
                    )
                elif dns_res.get("status") == "DNS_DEGRADATION":
                    anomalies.append(
                        AnomalySchema(
                            metric_name="dns_latency_ms",
                            observed_value=latency,
                            expected_value=300.0,
                            baseline_reference="Static threshold: 300ms",
                            severity="MEDIUM",
                            rule_triggered="DNS_THRESHOLD_EXCEEDED",
                            evidence_text=f"DNS latency {latency:.1f}ms is elevated above static threshold",
                        )
                    )

        # 2. TCP Anomalies
        if tcp_res:
            if tcp_res.get("status") == "TCP_CONNECTIVITY_FAILURE":
                anomalies.append(
                    AnomalySchema(
                        metric_name="tcp_connect",
                        observed_value=tcp_res.get("connect_latency_ms", 0.0),
                        expected_value=0.0,
                        baseline_reference="TCP handshake established",
                        severity="CRITICAL",
                        rule_triggered="TCP_CONNECTIVITY_FAILURE",
                        evidence_text=f"TCP 3-way handshake failed: {tcp_res.get('error_message')}",
                    )
                )
            else:
                latency = tcp_res.get("connect_latency_ms", 0.0)
                bl = baselines.get("tcp_latency_ms")
                if bl and bl.is_sufficient_evidence and latency > bl.p95:
                    anomalies.append(
                        AnomalySchema(
                            metric_name="tcp_latency_ms",
                            observed_value=latency,
                            expected_value=bl.p50,
                            baseline_reference=f"P95: {bl.p95}ms (P50: {bl.p50}ms)",
                            severity="HIGH",
                            rule_triggered="TCP_BASELINE_P95_EXCEEDED",
                            evidence_text=f"TCP connect latency {latency:.1f}ms exceeds historical P95 ({bl.p95:.1f}ms)",
                        )
                    )

        # 3. TLS Anomalies
        if tls_res:
            if tls_res.get("status") == "TLS_FAILURE":
                anomalies.append(
                    AnomalySchema(
                        metric_name="tls_handshake",
                        observed_value=tls_res.get("handshake_latency_ms", 0.0),
                        expected_value=0.0,
                        baseline_reference="Valid TLS certificate & cipher",
                        severity="CRITICAL",
                        rule_triggered="TLS_HANDSHAKE_FAILURE",
                        evidence_text=f"TLS handshake/validation failure: {tls_res.get('error_message')}",
                    )
                )
            elif tls_res.get("status") == "TLS_CERTIFICATE_EXPIRING":
                days = tls_res.get("days_to_expiration", 0)
                anomalies.append(
                    AnomalySchema(
                        metric_name="tls_cert_validity",
                        observed_value=float(days or 0),
                        expected_value=30.0,
                        baseline_reference="Expires > 30 days",
                        severity="HIGH",
                        rule_triggered="TLS_CERTIFICATE_EXPIRING",
                        evidence_text=f"Certificate expires in {days} days ({tls_res.get('cert_expires_at')})",
                    )
                )
            else:
                latency = tls_res.get("handshake_latency_ms", 0.0)
                bl = baselines.get("tls_latency_ms")
                if bl and bl.is_sufficient_evidence and latency > bl.p95:
                    anomalies.append(
                        AnomalySchema(
                            metric_name="tls_latency_ms",
                            observed_value=latency,
                            expected_value=bl.p50,
                            baseline_reference=f"P95: {bl.p95}ms (P50: {bl.p50}ms)",
                            severity="MEDIUM",
                            rule_triggered="TLS_BASELINE_P95_EXCEEDED",
                            evidence_text=f"TLS handshake latency {latency:.1f}ms exceeds historical P95 ({bl.p95:.1f}ms)",
                        )
                    )

        # 4. HTTP Anomalies
        if http_res:
            status_code = http_res.get("status_code")
            total_lat = http_res.get("total_latency_ms", 0.0)
            ttfb = http_res.get("ttfb_ms", 0.0)

            if status_code and status_code >= 500:
                anomalies.append(
                    AnomalySchema(
                        metric_name="http_status_code",
                        observed_value=float(status_code),
                        expected_value=200.0,
                        baseline_reference="HTTP 2xx Success",
                        severity="CRITICAL",
                        rule_triggered="HTTP_SERVER_ERROR",
                        evidence_text=f"Server returned HTTP {status_code}: {http_res.get('error_message')}",
                    )
                )
            elif status_code and (status_code == 404 or status_code == 429):
                anomalies.append(
                    AnomalySchema(
                        metric_name="http_status_code",
                        observed_value=float(status_code),
                        expected_value=200.0,
                        baseline_reference="HTTP 2xx Success",
                        severity="HIGH",
                        rule_triggered="HTTP_CLIENT_RESOURCE_ERROR",
                        evidence_text=f"HTTP response error {status_code}: {http_res.get('error_message')}",
                    )
                )

            # HTTP Latency vs Baseline
            bl = baselines.get("http_latency_ms")
            if bl and bl.is_sufficient_evidence and total_lat > bl.p95:
                anomalies.append(
                    AnomalySchema(
                        metric_name="http_latency_ms",
                        observed_value=total_lat,
                        expected_value=bl.p50,
                        baseline_reference=f"P95: {bl.p95}ms (P50: {bl.p50}ms)",
                        severity="HIGH",
                        rule_triggered="HTTP_BASELINE_P95_EXCEEDED",
                        evidence_text=f"HTTP total latency {total_lat:.1f}ms exceeds historical P95 ({bl.p95:.1f}ms)",
                    )
                )
            elif http_res.get("status") == "HTTP_APPLICATION_LATENCY":
                anomalies.append(
                    AnomalySchema(
                        metric_name="http_latency_ms",
                        observed_value=total_lat,
                        expected_value=1000.0,
                        baseline_reference="Static threshold: 1000ms",
                        severity="MEDIUM",
                        rule_triggered="HTTP_LATENCY_THRESHOLD_EXCEEDED",
                        evidence_text=f"HTTP response latency {total_lat:.1f}ms exceeded default threshold",
                    )
                )

        # 5. Network Path Anomalies
        if network_hops:
            timeout_hops = [h for h in network_hops if h.get("is_timeout")]
            if len(timeout_hops) > 0 and len(timeout_hops) == len(network_hops):
                anomalies.append(
                    AnomalySchema(
                        metric_name="network_packet_loss",
                        observed_value=100.0,
                        expected_value=0.0,
                        baseline_reference="Network path reachability",
                        severity="HIGH",
                        rule_triggered="NETWORK_TOTAL_PACKET_LOSS",
                        evidence_text="All intermediate network path probes timed out",
                    )
                )
            elif len(timeout_hops) > 1:
                anomalies.append(
                    AnomalySchema(
                        metric_name="network_packet_loss",
                        observed_value=float(len(timeout_hops)),
                        expected_value=0.0,
                        baseline_reference="0 dropped hops",
                        severity="MEDIUM",
                        rule_triggered="NETWORK_PARTIAL_PACKET_LOSS",
                        evidence_text=f"{len(timeout_hops)} intermediate hops exhibited timeouts / packet loss",
                    )
                )

        # 6. Host System Metrics Anomalies
        if system_metric:
            if system_metric.get("status") == "RESOURCE_PRESSURE":
                anomalies.append(
                    AnomalySchema(
                        metric_name="system_resources",
                        observed_value=system_metric.get("cpu_pct", 0.0),
                        expected_value=90.0,
                        baseline_reference="CPU/Memory < 90%",
                        severity="HIGH",
                        rule_triggered="SYSTEM_RESOURCE_PRESSURE",
                        evidence_text=f"Local system resource saturation: {system_metric.get('error_message')}",
                    )
                )
            elif system_metric.get("status") == "NETWORK_INTERFACE_ERRORS":
                anomalies.append(
                    AnomalySchema(
                        metric_name="interface_errors",
                        observed_value=float(system_metric.get("net_errin", 0) + system_metric.get("net_errout", 0)),
                        expected_value=0.0,
                        baseline_reference="0 interface errors",
                        severity="HIGH",
                        rule_triggered="INTERFACE_ERRORS_DETECTED",
                        evidence_text=f"Interface drops/errors observed: {system_metric.get('error_message')}",
                    )
                )

        return anomalies
