from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database.session import SessionLocal
from backend.app.security.ssrf import validate_and_parse_url, SSRFValidationError
from backend.app.collectors.dns import DnsCollector
from backend.app.collectors.tcp import TcpCollector
from backend.app.collectors.tls import TlsCollector
from backend.app.collectors.http import HttpCollector
from backend.app.collectors.network_path import NetworkPathCollector
from backend.app.collectors.linux_metrics import LinuxMetricsCollector
from backend.app.analysis.diagnosis import DiagnosisEngine
from backend.app.models.target import Target
from backend.app.models.session import DiagnosticSession
from backend.app.models.layer_results import (
    DnsResult,
    TcpResult,
    TlsResult,
    HttpResult,
    NetworkHop,
    SystemMetric,
    MetricSample,
)
from backend.app.models.diagnosis import (
    Anomaly,
    Diagnosis,
    DiagnosisEvidence,
    Recommendation,
    IncidentEvent,
)
from backend.app.observability.metrics import (
    DIAGNOSTICS_TOTAL,
    DIAGNOSTICS_FAILED_TOTAL,
    DIAGNOSTIC_DURATION_SECONDS,
    DNS_LATENCY_SECONDS,
    TCP_LATENCY_SECONDS,
    TLS_LATENCY_SECONDS,
    HTTP_LATENCY_SECONDS,
    ANOMALIES_TOTAL,
    DIAGNOSES_TOTAL,
)

logger = logging.getLogger("netpath.service.diagnostic")


class DiagnosticService:
    def __init__(self) -> None:
        self.dns_collector = DnsCollector(timeout_seconds=settings.PROBE_TIMEOUT_SECONDS)
        self.tcp_collector = TcpCollector(timeout_seconds=settings.PROBE_TIMEOUT_SECONDS)
        self.tls_collector = TlsCollector(timeout_seconds=settings.PROBE_TIMEOUT_SECONDS)
        self.http_collector = HttpCollector(timeout_seconds=settings.PROBE_TIMEOUT_SECONDS)
        self.path_collector = NetworkPathCollector(timeout_seconds=settings.PROBE_TIMEOUT_SECONDS)
        self.sys_collector = LinuxMetricsCollector()
        self.diagnosis_engine = DiagnosisEngine()

    def get_or_create_target(self, db: Session, url: str) -> Target:
        scheme, hostname, port, path = validate_and_parse_url(url)
        normalized_url = f"{scheme}://{hostname}:{port}{path}" if (
            (scheme == "http" and port != 80) or (scheme == "https" and port != 443)
        ) else f"{scheme}://{hostname}{path}"

        target = db.execute(select(Target).where(Target.url == normalized_url)).scalar_one_or_none()
        if not target:
            target = Target(
                url=normalized_url,
                hostname=hostname,
                port=port,
                scheme=scheme,
                path=path,
            )
            db.add(target)
            db.commit()
            db.refresh(target)
        return target

    async def execute_diagnostic_async(self, session_id: str, url: str) -> None:
        """Runs the diagnostic asynchronously in background and saves all results to DB."""
        # Run blocking execution in thread pool to not block asyncio event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.execute_diagnostic_sync, session_id, url)

    def execute_diagnostic_sync(self, session_id: str, url: str) -> DiagnosticSession:
        """Synchronous execution of the full 7-step diagnostic workflow."""
        start_mono = time.perf_counter()
        db: Session = SessionLocal()

        session = db.execute(select(DiagnosticSession).where(DiagnosticSession.id == session_id)).scalar_one_or_none()
        if not session:
            logger.error(f"Session {session_id} not found.")
            db.close()
            raise ValueError(f"Session {session_id} not found")

        correlation_id = session.correlation_id
        target = session.target
        target_host = target.hostname
        target_port = target.port
        is_https = target.scheme.lower() == "https"

        timeline_records: List[IncidentEvent] = []

        def log_event(event_type: str, layer: str, message: str, status: str = "SUCCESS") -> None:
            ev = IncidentEvent(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                event_type=event_type,
                layer=layer,
                message=message,
                status=status,
            )
            timeline_records.append(ev)
            logger.info(
                message,
                extra={
                    "correlation_id": correlation_id,
                    "session_id": session_id,
                    "event": event_type,
                    "layer": layer,
                }
            )

        try:
            log_event("START", "System", f"Starting deterministic diagnostic session for {url}")

            # ---------------------------------------------------------
            # 1. DNS Resolution
            # ---------------------------------------------------------
            log_event("DNS_START", "DNS", f"Querying DNS resolver for hostname '{target_host}'")
            dns_res = self.dns_collector.collect(target_host)
            dns_status = dns_res.get("status", "SUCCESS")
            dns_latency = dns_res.get("latency_ms", 0.0)

            if dns_status == "SUCCESS":
                DNS_LATENCY_SECONDS.observe(dns_latency / 1000.0)
                log_event("DNS_SUCCESS", "DNS", f"DNS resolved in {dns_latency:.1f}ms to {dns_res.get('addresses')}")
                # Save metric sample
                db.add(MetricSample(target_id=target.id, metric_name="dns_latency_ms", value=dns_latency))
            elif dns_status == "DNS_DEGRADATION":
                DNS_LATENCY_SECONDS.observe(dns_latency / 1000.0)
                log_event("DNS_DEGRADED", "DNS", f"DNS resolution degraded ({dns_latency:.1f}ms): {dns_res.get('error_message')}", status="DEGRADED")
                db.add(MetricSample(target_id=target.id, metric_name="dns_latency_ms", value=dns_latency))
            else:
                log_event("DNS_FAILED", "DNS", f"DNS resolution failed: {dns_res.get('error_message')}", status="FAILED")

            # ---------------------------------------------------------
            # 2. TCP Connectivity
            # ---------------------------------------------------------
            tcp_res = None
            resolved_ips = dns_res.get("addresses", [])
            primary_ip = resolved_ips[0] if resolved_ips else target_host

            if dns_status != "DNS_FAILURE":
                log_event("TCP_START", "TCP", f"Initiating TCP handshake to {primary_ip}:{target_port}")
                tcp_res = self.tcp_collector.collect(destination_ip=primary_ip, destination_port=target_port)
                tcp_status = tcp_res.get("status", "SUCCESS")
                tcp_lat = tcp_res.get("connect_latency_ms", 0.0)

                if tcp_status == "SUCCESS":
                    TCP_LATENCY_SECONDS.observe(tcp_lat / 1000.0)
                    log_event("TCP_SUCCESS", "TCP", f"TCP connection established in {tcp_lat:.1f}ms")
                    db.add(MetricSample(target_id=target.id, metric_name="tcp_latency_ms", value=tcp_lat))
                elif tcp_status == "TCP_DEGRADATION":
                    TCP_LATENCY_SECONDS.observe(tcp_lat / 1000.0)
                    log_event("TCP_DEGRADED", "TCP", f"TCP connect latency degraded ({tcp_lat:.1f}ms)", status="DEGRADED")
                    db.add(MetricSample(target_id=target.id, metric_name="tcp_latency_ms", value=tcp_lat))
                else:
                    log_event("TCP_FAILED", "TCP", f"TCP handshake failed: {tcp_res.get('error_message')}", status="FAILED")
            else:
                log_event("TCP_SKIPPED", "TCP", "TCP handshake skipped due to DNS resolution failure", status="INFO")

            # ---------------------------------------------------------
            # 3. TLS Handshake (if HTTPS)
            # ---------------------------------------------------------
            tls_res = None
            if is_https and tcp_res and tcp_res.get("status") != "TCP_CONNECTIVITY_FAILURE":
                log_event("TLS_START", "TLS", f"Negotiating TLS handshake with {target_host} ({primary_ip}:{target_port})")
                tls_res = self.tls_collector.collect(hostname=target_host, destination_ip=primary_ip, port=target_port)
                tls_status = tls_res.get("status", "SUCCESS")
                tls_lat = tls_res.get("handshake_latency_ms", 0.0)

                if tls_status == "SUCCESS":
                    TLS_LATENCY_SECONDS.observe(tls_lat / 1000.0)
                    log_event("TLS_SUCCESS", "TLS", f"TLS {tls_res.get('tls_version')} handshake negotiated in {tls_lat:.1f}ms (Cipher: {tls_res.get('cipher')})")
                    db.add(MetricSample(target_id=target.id, metric_name="tls_latency_ms", value=tls_lat))
                elif tls_status == "TLS_CERTIFICATE_EXPIRING":
                    TLS_LATENCY_SECONDS.observe(tls_lat / 1000.0)
                    log_event("TLS_EXPIRING", "TLS", f"TLS certificate expiring soon ({tls_res.get('days_to_expiration')} days left)", status="DEGRADED")
                    db.add(MetricSample(target_id=target.id, metric_name="tls_latency_ms", value=tls_lat))
                else:
                    log_event("TLS_FAILED", "TLS", f"TLS handshake/certificate failure: {tls_res.get('error_message')}", status="FAILED")
            elif is_https:
                log_event("TLS_SKIPPED", "TLS", "TLS handshake skipped due to lower-layer connection failure", status="INFO")

            # ---------------------------------------------------------
            # 4. HTTP Application Probe
            # ---------------------------------------------------------
            http_res = None
            if (not is_https and tcp_res and tcp_res.get("status") != "TCP_CONNECTIVITY_FAILURE") or (
                is_https and tls_res and tls_res.get("status") != "TLS_FAILURE"
            ) or (tcp_res and tcp_res.get("status") == "SUCCESS"):
                log_event("HTTP_START", "HTTP", f"Sending HTTP GET request to {url}")
                http_res = self.http_collector.collect(url)
                http_status = http_res.get("status", "SUCCESS")
                code = http_res.get("status_code")
                tot_lat = http_res.get("total_latency_ms", 0.0)
                ttfb = http_res.get("ttfb_ms", 0.0)

                HTTP_LATENCY_SECONDS.observe(tot_lat / 1000.0)
                db.add(MetricSample(target_id=target.id, metric_name="http_latency_ms", value=tot_lat))
                db.add(MetricSample(target_id=target.id, metric_name="http_ttfb_ms", value=ttfb))

                if code and 200 <= code < 400:
                    if http_status == "HTTP_APPLICATION_LATENCY":
                        log_event("HTTP_LATENCY", "HTTP", f"HTTP {code} received, but latency was high ({tot_lat:.1f}ms, TTFB: {ttfb:.1f}ms)", status="DEGRADED")
                    else:
                        log_event("HTTP_SUCCESS", "HTTP", f"HTTP {code} OK ({tot_lat:.1f}ms, TTFB: {ttfb:.1f}ms, Bytes: {http_res.get('response_bytes')})")
                else:
                    log_event("HTTP_ERROR", "HTTP", f"HTTP server returned code {code} ({http_res.get('error_message')})", status="FAILED")
            else:
                log_event("HTTP_SKIPPED", "HTTP", "HTTP request skipped due to network/TLS connectivity failure", status="INFO")

            # ---------------------------------------------------------
            # 5. Network Path Hop Analysis
            # ---------------------------------------------------------
            log_event("PATH_START", "Network", f"Probing network path hops toward {primary_ip}")
            network_hops_data = self.path_collector.collect(target_host, primary_ip)
            log_event("PATH_COMPLETE", "Network", f"Network path inspection completed with {len(network_hops_data)} hops")

            # ---------------------------------------------------------
            # 6. Linux System Resource Metrics
            # ---------------------------------------------------------
            log_event("SYSTEM_START", "System", "Collecting local system metrics (CPU, Memory, Interface I/O)")
            sys_metrics_data = self.sys_collector.collect()
            log_event("SYSTEM_COMPLETE", "System", f"System metrics: CPU={sys_metrics_data.get('cpu_pct')}%, Mem={sys_metrics_data.get('memory_pct')}%")

            # ---------------------------------------------------------
            # 7. Analysis & Deterministic Root-Cause Diagnosis
            # ---------------------------------------------------------
            log_event("ANALYSIS_START", "Analysis", "Evaluating historical baselines and multi-layer correlation")
            analysis_output = self.diagnosis_engine.diagnose(
                db=db,
                target_id=target.id,
                dns_res=dns_res,
                tcp_res=tcp_res,
                tls_res=tls_res,
                http_res=http_res,
                network_hops=network_hops_data,
                system_metric=sys_metrics_data,
            )

            diag: DiagnosisSchema = analysis_output["diagnosis"]
            anomalies: List[AnomalySchema] = analysis_output["anomalies"]

            # Record Prometheus metrics
            for a in anomalies:
                ANOMALIES_TOTAL.labels(metric=a.metric_name, severity=a.severity).inc()
            DIAGNOSES_TOTAL.labels(category=diag.category, severity=diag.severity).inc()

            log_event(
                "ROOT_CAUSE_IDENTIFIED",
                "Analysis",
                f"Deterministic Diagnosis: {diag.category} (Severity: {diag.severity}, Evidence Score: {diag.evidence_score}). {diag.summary}",
                status="FAILED" if diag.severity in ("CRITICAL", "HIGH") else "SUCCESS"
            )

            # ---------------------------------------------------------
            # Persist All Results Atomically
            # ---------------------------------------------------------
            # 1. DNS Result
            db.add(
                DnsResult(
                    session_id=session_id,
                    resolver=dns_res.get("resolver", "system"),
                    latency_ms=dns_res.get("latency_ms", 0.0),
                    record_type=dns_res.get("record_type", "A"),
                    addresses={"ips": dns_res.get("addresses", [])},
                    status=dns_res.get("status", "SUCCESS"),
                    error_message=dns_res.get("error_message"),
                )
            )

            # 2. TCP Result
            if tcp_res:
                db.add(
                    TcpResult(
                        session_id=session_id,
                        destination_ip=tcp_res.get("destination_ip", primary_ip),
                        destination_port=tcp_res.get("destination_port", target_port),
                        connect_latency_ms=tcp_res.get("connect_latency_ms", 0.0),
                        status=tcp_res.get("status", "SUCCESS"),
                        error_message=tcp_res.get("error_message"),
                    )
                )

            # 3. TLS Result
            if tls_res:
                db.add(
                    TlsResult(
                        session_id=session_id,
                        tls_version=tls_res.get("tls_version"),
                        cipher=tls_res.get("cipher"),
                        cert_subject=tls_res.get("cert_subject"),
                        cert_issuer=tls_res.get("cert_issuer"),
                        cert_expires_at=tls_res.get("cert_expires_at"),
                        days_to_expiration=tls_res.get("days_to_expiration"),
                        handshake_latency_ms=tls_res.get("handshake_latency_ms", 0.0),
                        is_valid=tls_res.get("is_valid", True),
                        status=tls_res.get("status", "SUCCESS"),
                        error_message=tls_res.get("error_message"),
                    )
                )

            # 4. HTTP Result
            if http_res:
                db.add(
                    HttpResult(
                        session_id=session_id,
                        status_code=http_res.get("status_code"),
                        ttfb_ms=http_res.get("ttfb_ms", 0.0),
                        total_latency_ms=http_res.get("total_latency_ms", 0.0),
                        response_bytes=http_res.get("response_bytes", 0),
                        redirect_count=http_res.get("redirect_count", 0),
                        headers=http_res.get("headers"),
                        status=http_res.get("status", "SUCCESS"),
                        error_message=http_res.get("error_message"),
                    )
                )

            # 5. Network Hops
            for hop in network_hops_data:
                db.add(
                    NetworkHop(
                        session_id=session_id,
                        hop_number=hop.get("hop_number", 1),
                        ip_address=hop.get("ip_address"),
                        hostname=hop.get("hostname"),
                        rtt_ms=hop.get("rtt_ms"),
                        is_timeout=hop.get("is_timeout", False),
                        packet_loss_pct=hop.get("packet_loss_pct", 0.0),
                    )
                )

            # 6. System Metrics
            db.add(
                SystemMetric(
                    session_id=session_id,
                    cpu_pct=sys_metrics_data.get("cpu_pct", 0.0),
                    memory_pct=sys_metrics_data.get("memory_pct", 0.0),
                    load_1m=sys_metrics_data.get("load_1m", 0.0),
                    load_5m=sys_metrics_data.get("load_5m", 0.0),
                    load_15m=sys_metrics_data.get("load_15m", 0.0),
                    net_bytes_sent=sys_metrics_data.get("net_bytes_sent", 0),
                    net_bytes_recv=sys_metrics_data.get("net_bytes_recv", 0),
                    net_errin=sys_metrics_data.get("net_errin", 0),
                    net_errout=sys_metrics_data.get("net_errout", 0),
                    net_dropin=sys_metrics_data.get("net_dropin", 0),
                    net_dropout=sys_metrics_data.get("net_dropout", 0),
                    status=sys_metrics_data.get("status", "SUCCESS"),
                )
            )

            # 7. Anomalies
            for a in anomalies:
                db.add(
                    Anomaly(
                        session_id=session_id,
                        metric_name=a.metric_name,
                        observed_value=a.observed_value,
                        expected_value=a.expected_value,
                        baseline_reference=a.baseline_reference,
                        severity=a.severity,
                        rule_triggered=a.rule_triggered,
                        evidence_text=a.evidence_text,
                    )
                )

            # 8. Diagnosis + Evidence + Recommendations
            diag_model = Diagnosis(
                session_id=session_id,
                category=diag.category,
                severity=diag.severity,
                evidence_score=diag.evidence_score,
                affected_layer=diag.affected_layer,
                summary=diag.summary,
            )
            db.add(diag_model)
            db.flush()

            for ev_item in diag.evidence_items:
                db.add(
                    DiagnosisEvidence(
                        diagnosis_id=diag_model.id,
                        weight=ev_item.weight,
                        description=ev_item.description,
                        metric_name=ev_item.metric_name,
                    )
                )

            for rec in diag.recommendations:
                db.add(
                    Recommendation(
                        diagnosis_id=diag_model.id,
                        action_order=rec.action_order,
                        action_text=rec.action_text,
                    )
                )

            # 9. Timeline Events
            for ev in timeline_records:
                db.add(ev)

            # 10. Update Session State
            duration_total_ms = (time.perf_counter() - start_mono) * 1000.0
            session.status = "COMPLETED"
            session.completed_at = datetime.utcnow()
            session.duration_ms = round(duration_total_ms, 2)

            db.commit()
            db.refresh(session)

            DIAGNOSTICS_TOTAL.labels(target_host=target_host, status="COMPLETED").inc()
            DIAGNOSTIC_DURATION_SECONDS.observe(duration_total_ms / 1000.0)

            return session

        except Exception as ex:
            db.rollback()
            dur = (time.perf_counter() - start_mono) * 1000.0
            logger.exception(f"Diagnostic session {session_id} failed with error: {ex}")
            session.status = "FAILED"
            session.error_message = str(ex)
            session.completed_at = datetime.utcnow()
            session.duration_ms = round(dur, 2)
            db.commit()

            DIAGNOSTICS_FAILED_TOTAL.labels(target_host=target_host).inc()
            raise
        finally:
            db.close()
