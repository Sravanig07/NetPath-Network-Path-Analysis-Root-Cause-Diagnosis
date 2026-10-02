from __future__ import annotations

from prometheus_client import Counter, Histogram

# Prometheus application metrics
DIAGNOSTICS_TOTAL = Counter(
    "netpath_diagnostics_total",
    "Total count of diagnostic sessions executed",
    ["target_host", "status"]
)

DIAGNOSTICS_FAILED_TOTAL = Counter(
    "netpath_diagnostics_failed_total",
    "Total count of diagnostic sessions that failed to execute",
    ["target_host"]
)

DIAGNOSTIC_DURATION_SECONDS = Histogram(
    "netpath_diagnostic_duration_seconds",
    "Histogram of total diagnostic workflow duration in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

DNS_LATENCY_SECONDS = Histogram(
    "netpath_dns_latency_seconds",
    "DNS resolution duration in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

TCP_LATENCY_SECONDS = Histogram(
    "netpath_tcp_latency_seconds",
    "TCP 3-way handshake connect latency in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

TLS_LATENCY_SECONDS = Histogram(
    "netpath_tls_latency_seconds",
    "TLS handshake duration in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

HTTP_LATENCY_SECONDS = Histogram(
    "netpath_http_latency_seconds",
    "HTTP total request/response duration in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ANOMALIES_TOTAL = Counter(
    "netpath_anomalies_total",
    "Total anomalies detected across layers",
    ["metric", "severity"]
)

DIAGNOSES_TOTAL = Counter(
    "netpath_diagnoses_total",
    "Total diagnoses categorized by root cause",
    ["category", "severity"]
)
