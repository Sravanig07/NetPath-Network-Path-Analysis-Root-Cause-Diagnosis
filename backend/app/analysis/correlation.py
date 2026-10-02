from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from backend.app.schemas.analysis import AnomalySchema, EvidenceItemSchema
from backend.app.config import settings

logger = logging.getLogger("netpath.analysis.correlation")


class CorrelationEngine:
    """
    Correlates cross-layer symptoms across DNS, TCP, TLS, HTTP, Network, and Host metrics.
    Distinguishes primary root causes from downstream cascade symptoms.
    """

    def correlate(
        self,
        dns_res: Optional[Dict[str, Any]],
        tcp_res: Optional[Dict[str, Any]],
        tls_res: Optional[Dict[str, Any]],
        http_res: Optional[Dict[str, Any]],
        network_hops: List[Dict[str, Any]],
        system_metric: Optional[Dict[str, Any]],
        anomalies: List[AnomalySchema],
    ) -> Tuple[str, str, str, str, List[EvidenceItemSchema]]:
        """
        Returns:
            (category, severity, affected_layer, summary, evidence_items)
        """
        evidence_items: List[EvidenceItemSchema] = []

        dns_status = (dns_res or {}).get("status", "SUCCESS")
        tcp_status = (tcp_res or {}).get("status", "SUCCESS")
        tls_status = (tls_res or {}).get("status", "SUCCESS")
        http_status = (http_res or {}).get("status", "SUCCESS")
        sys_status = (system_metric or {}).get("status", "SUCCESS")

        anomaly_rules = {a.rule_triggered: a for a in anomalies}

        # -------------------------------------------------------------
        # 1. DNS Layer Failures & Degradations
        # -------------------------------------------------------------
        if dns_status == "DNS_FAILURE":
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_DNS_ANOMALY,
                    description=f"DNS resolution failed: {dns_res.get('error_message')}",
                    metric_name="dns_resolution",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=2,
                    description="Downstream TCP and HTTP requests were blocked by DNS failure.",
                    metric_name="dependency_flow",
                )
            )
            return (
                "DNS_FAILURE",
                "CRITICAL",
                "DNS",
                "Target hostname could not be resolved by configured DNS resolvers.",
                evidence_items,
            )

        if "DNS_BASELINE_P95_EXCEEDED" in anomaly_rules or dns_status == "DNS_DEGRADATION":
            a = anomaly_rules.get("DNS_BASELINE_P95_EXCEEDED") or anomaly_rules.get("DNS_THRESHOLD_EXCEEDED")
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_DNS_ANOMALY,
                    description=a.evidence_text if a else "DNS resolution latency is abnormally high",
                    metric_name="dns_latency_ms",
                )
            )
            if tcp_status == "SUCCESS" and http_status == "SUCCESS":
                evidence_items.append(
                    EvidenceItemSchema(
                        weight=1,
                        description="TCP handshake and HTTP response executed within normal bounds once resolved.",
                        metric_name="tcp_connect",
                    )
                )
            return (
                "DNS_DEGRADATION",
                "HIGH",
                "DNS",
                "DNS resolution latency is significantly above baseline, delaying initial connection establishment.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 2. Host System Resource Pressure / Local Interface Errors
        # -------------------------------------------------------------
        if sys_status == "NETWORK_INTERFACE_ERRORS":
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_INTERFACE_DROPS,
                    description=f"Local network interface drops/errors observed: {system_metric.get('error_message')}",
                    metric_name="interface_errors",
                )
            )
            return (
                "NETWORK_INTERFACE_ERRORS",
                "HIGH",
                "System",
                "Host network interface packet drops or hardware errors are impacting network performance.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 3. TCP Layer Connectivity & Latency
        # -------------------------------------------------------------
        if tcp_status == "TCP_CONNECTIVITY_FAILURE":
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_TCP_FAILURE,
                    description=f"TCP 3-way handshake failed: {tcp_res.get('error_message')}",
                    metric_name="tcp_connect",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=1,
                    description=f"DNS resolution succeeded ({dns_res.get('latency_ms', 0)}ms) before TCP failure.",
                    metric_name="dns_resolution",
                )
            )
            return (
                "TCP_CONNECTIVITY_FAILURE",
                "CRITICAL",
                "TCP",
                f"TCP connection could not be established to {tcp_res.get('destination_ip')}:{tcp_res.get('destination_port')}.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 4. Network Path Degradation / Packet Loss
        # -------------------------------------------------------------
        has_network_loss = any(a.rule_triggered in ("NETWORK_TOTAL_PACKET_LOSS", "NETWORK_PARTIAL_PACKET_LOSS") for a in anomalies)
        if has_network_loss and (tcp_status == "TCP_DEGRADATION" or "TCP_BASELINE_P95_EXCEEDED" in anomaly_rules):
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_PACKET_LOSS,
                    description="Packet loss or timeouts observed on intermediate routing hops.",
                    metric_name="network_packet_loss",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_TCP_DEGRADATION,
                    description=f"TCP connect latency elevated ({tcp_res.get('connect_latency_ms', 0)}ms) due to retransmissions.",
                    metric_name="tcp_latency_ms",
                )
            )
            return (
                "NETWORK_PACKET_LOSS",
                "HIGH",
                "Network",
                "Intermediate network path packet loss and elevated round-trip times are degrading TCP connections.",
                evidence_items,
            )

        if tcp_status == "TCP_DEGRADATION" or "TCP_BASELINE_P95_EXCEEDED" in anomaly_rules:
            a = anomaly_rules.get("TCP_BASELINE_P95_EXCEEDED")
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_TCP_DEGRADATION,
                    description=a.evidence_text if a else "TCP handshake latency exceeded normal limits",
                    metric_name="tcp_latency_ms",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=1,
                    description=f"DNS completed normally in {dns_res.get('latency_ms', 0)}ms.",
                    metric_name="dns_latency_ms",
                )
            )
            return (
                "TCP_DEGRADATION",
                "MEDIUM",
                "TCP",
                "TCP handshake latency is elevated, indicating network congestion, routing delays, or SYN queue delay.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 5. TLS Layer
        # -------------------------------------------------------------
        if tls_status == "TLS_FAILURE":
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_TLS_FAILURE,
                    description=f"TLS handshake/validation failed: {tls_res.get('error_message')}",
                    metric_name="tls_handshake",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=1,
                    description="TCP 3-way handshake established successfully before TLS failure.",
                    metric_name="tcp_connect",
                )
            )
            return (
                "TLS_FAILURE",
                "CRITICAL",
                "TLS",
                "TLS negotiation failed due to certificate invalidity, hostname mismatch, or protocol/cipher incompatibility.",
                evidence_items,
            )

        if tls_status == "TLS_CERTIFICATE_EXPIRING":
            days = tls_res.get("days_to_expiration", 0)
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_TLS_EXPIRING,
                    description=f"Target SSL certificate will expire in {days} days ({tls_res.get('cert_expires_at')}).",
                    metric_name="tls_cert_validity",
                )
            )
            return (
                "TLS_CERTIFICATE_EXPIRING",
                "HIGH",
                "TLS",
                f"SSL certificate is nearing expiration ({days} days remaining).",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 6. HTTP Application Layer (Errors vs Latency)
        # -------------------------------------------------------------
        if http_res and http_res.get("status_code", 0) >= 500:
            code = http_res.get("status_code")
            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_HTTP_ERROR,
                    description=f"Server returned HTTP status code {code}: {http_res.get('error_message')}",
                    metric_name="http_status_code",
                )
            )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=2,
                    description="DNS, TCP connect, and TLS handshakes were nominal.",
                    metric_name="lower_layers_nominal",
                )
            )
            return (
                "HTTP_APPLICATION_ERROR",
                "CRITICAL",
                "HTTP",
                f"Application upstream returned HTTP {code} error despite healthy lower-layer network connections.",
                evidence_items,
            )

        if http_res and http_res.get("status_code") in (404, 429):
            code = http_res.get("status_code")
            evidence_items.append(
                EvidenceItemSchema(
                    weight=3,
                    description=f"HTTP response error {code}: {http_res.get('error_message')}",
                    metric_name="http_status_code",
                )
            )
            return (
                "HTTP_APPLICATION_ERROR",
                "MEDIUM",
                "HTTP",
                f"Application returned client-side error code {code}.",
                evidence_items,
            )

        if "HTTP_BASELINE_P95_EXCEEDED" in anomaly_rules or http_status == "HTTP_APPLICATION_LATENCY":
            a = anomaly_rules.get("HTTP_BASELINE_P95_EXCEEDED")
            ttfb = http_res.get("ttfb_ms", 0.0)
            total = http_res.get("total_latency_ms", 0.0)

            evidence_items.append(
                EvidenceItemSchema(
                    weight=settings.SCORE_HTTP_LATENCY,
                    description=a.evidence_text if a else f"HTTP latency ({total:.1f}ms) exceeded threshold",
                    metric_name="http_latency_ms",
                )
            )
            if ttfb > 0 and total > 0:
                ttfb_ratio = (ttfb / total) * 100.0
                evidence_items.append(
                    EvidenceItemSchema(
                        weight=2,
                        description=f"TTFB was {ttfb:.1f}ms ({ttfb_ratio:.0f}% of total duration), indicating server-side backend processing time.",
                        metric_name="http_ttfb_ms",
                    )
                )
            evidence_items.append(
                EvidenceItemSchema(
                    weight=2,
                    description=f"DNS ({dns_res.get('latency_ms', 0):.1f}ms) and TCP ({tcp_res.get('connect_latency_ms', 0):.1f}ms) completed within baseline.",
                    metric_name="network_layers_nominal",
                )
            )
            return (
                "HTTP_APPLICATION_LATENCY",
                "HIGH",
                "HTTP",
                "Lower network layers are nominal, but server application response time significantly exceeds baseline.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 7. Local Host Resource Pressure
        # -------------------------------------------------------------
        if sys_status == "RESOURCE_PRESSURE":
            evidence_items.append(
                EvidenceItemSchema(
                    weight=2,
                    description=f"Host CPU/Memory pressure: {system_metric.get('error_message')}",
                    metric_name="system_resources",
                )
            )
            return (
                "RESOURCE_PRESSURE",
                "MEDIUM",
                "System",
                "Client or host system is experiencing severe CPU or memory saturation.",
                evidence_items,
            )

        # -------------------------------------------------------------
        # 8. Nominal / Insufficient Evidence
        # -------------------------------------------------------------
        if anomalies:
            for a in anomalies:
                evidence_items.append(
                    EvidenceItemSchema(
                        weight=1,
                        description=a.evidence_text,
                        metric_name=a.metric_name,
                    )
                )
            return (
                "INSUFFICIENT_EVIDENCE",
                "LOW",
                "General",
                "Minor metric variations were observed, but no conclusive root-cause pattern was matched.",
                evidence_items,
            )

        evidence_items.append(
            EvidenceItemSchema(
                weight=1,
                description="All layers (DNS, TCP, TLS, HTTP, Network, System) completed within expected parameters.",
                metric_name="all_nominal",
            )
        )
        return (
            "INSUFFICIENT_EVIDENCE",
            "INFO",
            "None",
            "All diagnostic probes succeeded and operate within normal baseline parameters.",
            evidence_items,
        )
