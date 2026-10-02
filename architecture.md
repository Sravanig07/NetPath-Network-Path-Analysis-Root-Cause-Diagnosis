# Architecture Design: NetPath — Deterministic Network Path Analysis & Root-Cause Diagnosis Platform

## 1. System Overview

NetPath is a deterministic, explainable network performance and root-cause analysis platform. Given an endpoint (e.g. `https://service.example.com`), it diagnoses the underlying root cause of latency, failure, or degradation across the complete OSI / TCP-IP request path:

```
Target URL 
   ↓ 
1. SSRF & Scheme Validation
   ↓
2. DNS Collector (dnspython / system resolver)
   ↓
3. TCP Handshake Collector (socket connect)
   ↓
4. TLS Collector (ssl.SSLContext handshake & peer certificate)
   ↓
5. HTTP Application Collector (httpx async, TTFB & latency)
   ↓
6. Network Path Collector (traceroute / tracepath / socket probes)
   ↓
7. Linux / System Collector (psutil / /proc metrics)
   ↓
8. Historical Baseline Engine (MySQL sample persistence, P50/P95/P99, StdDev)
   ↓
9. Anomaly Detection Engine (Thresholds & Baseline Deviations)
   ↓
10. Cross-Layer Correlation Engine (Multi-Symptom Synthesis)
   ↓
11. Evidence Scoring (+3, +2 explainable points)
   ↓
12. Deterministic Root-Cause Diagnosis (13 Categories)
   ↓
13. Actionable Recommendations & Incident Replay
```

---

## 2. Architecture Principles

### Determinism & Explainability
- **No LLM in the core diagnosis**: LLM hallucination and probabilistic unpredictability are avoided in the diagnostic path. The system operates strictly deterministically.
- **No fragile spaghetti if/else statements**: The analysis is modularized into discrete stages: Collectors $\to$ Normalized Metrics $\to$ Baselines $\to$ Anomalies $\to$ Correlation Matrix $\to$ Evidence Scoring $\to$ Diagnosis $\to$ Actionable Recommendations.
- **Evidence-based Scoring**: Every diagnosis includes an explicit **Evidence Score** with an itemized points breakdown (e.g., `+3 packet loss`, `+2 HTTP latency > P95`, `+2 TTFB 98% of total duration`).
- **Distinguish Observation from Inference**: Raw telemetry observations (measured milliseconds, status codes, certificate expiration dates) are stored separately from analytical inferences.

---

## 3. Layer-by-Layer Diagnostic Specification

### Layer 1: DNS Resolution
- **Technology**: `dnspython` (`dns.resolver.Resolver`) with fallback to `socket.getaddrinfo`.
- **Metrics Collected**: Resolver IP, query start/end, resolution duration (`latency_ms`), record types (`A`, `AAAA`, `CNAME`), resolved IP addresses.
- **Failure Classification**:
  - `DNS_FAILURE`: NXDOMAIN, query timeout, or no records returned.
  - `DNS_DEGRADATION`: Query latency exceeds historical P95 baseline or static threshold (300ms).

### Layer 2: TCP Connection Handshake
- **Technology**: Non-blocking Python `socket` module with monotonic timers.
- **Metrics Collected**: Destination IP, destination port, 3-way handshake connect latency (`connect_latency_ms`), error codes (ECONNREFUSED, ETIMEDOUT, ENETUNREACH, EHOSTUNREACH).
- **Failure Classification**:
  - `TCP_CONNECTIVITY_FAILURE`: Connection refused (daemon down/firewalled), timeout, or host unreachable.
  - `TCP_DEGRADATION`: Connect latency exceeds P95 baseline or static threshold (250ms), indicating SYN queue delays or network congestion.

### Layer 3: TLS / SSL Negotiation
- **Technology**: Python `ssl.create_default_context()` with certificate verification enabled.
- **Metrics Collected**: TLS protocol version (TLSv1.2, TLSv1.3), cipher suite name, peer certificate subject and issuer, certificate validity window (`notBefore`, `notAfter`), days remaining until expiration (`days_to_expiration`), handshake duration.
- **Failure Classification**:
  - `TLS_FAILURE`: Handshake negotiation error, certificate verification error (hostname mismatch, expired certificate, self-signed untrusted CA).
  - `TLS_CERTIFICATE_EXPIRING`: Valid certificate nearing expiration (< 30 days remaining).

### Layer 4: HTTP Application Probe
- **Technology**: `httpx.AsyncClient` with custom streaming hooks.
- **Metrics Collected**: Time-To-First-Byte (`ttfb_ms`), total request duration (`total_latency_ms`), HTTP status code, response body byte count, redirect count, diagnostic response headers (`Server`, `Cache-Control`, `Retry-After`, etc.).
- **Failure Classification**:
  - `HTTP_APPLICATION_ERROR`: Server returned 500, 502, 503, 504, 404, or 429.
  - `HTTP_APPLICATION_LATENCY`: Status code is 2xx, but response duration exceeds historical P95 baseline or static threshold (1,000ms), with high TTFB indicating backend database or application contention.

### Layer 5: Network Path Analysis
- **Technology**: Safe subprocess invocation of `traceroute` / `tracepath` with sanitized arguments (`shell=False`, timeout=8s) and non-root socket probe fallback.
- **Metrics Collected**: Hop number, IP address, reverse hostname, round-trip time (`rtt_ms`), timeout indicators, packet loss percentage.
- **Failure Classification**:
  - `NETWORK_PACKET_LOSS`: Multiple intermediate hops timing out or packet loss > 5% correlated with elevated TCP connect latency.
  - `NETWORK_LATENCY`: Progressive RTT surge across intermediate transit hops.

### Layer 6: Linux System Resource Telemetry
- **Technology**: `psutil` + `/proc/loadavg` + `/proc/net/dev`.
- **Metrics Collected**: CPU utilization %, memory utilization %, 1m/5m/15m load averages, network interface transmitted/received bytes, packet drop counters (`dropin`, `dropout`), packet error counters (`net_errin`, `net_errout`).
- **Failure Classification**:
  - `RESOURCE_PRESSURE`: Host CPU > 90% or memory > 90%.
  - `NETWORK_INTERFACE_ERRORS`: Interface errors or drop counters elevated.

---

## 4. Historical Baseline Engine & Sample Safeguards

Single measurements can be misleading due to transient jitter. NetPath persists metric samples for every target in MySQL table `metric_samples`:
- `dns_latency_ms`
- `tcp_latency_ms`
- `tls_latency_ms`
- `http_latency_ms`
- `http_ttfb_ms`

### Statistical Percentiles Computed
- $\text{Count}$
- $\text{Min}$ and $\text{Max}$
- $\text{Mean}$ and $\text{Median}$
- $\text{P50}$, $\text{P95}$, $\text{P99}$
- $\text{Standard Deviation}$ ($\sigma$)

### Minimum Sample Safeguard
To prevent false-positive anomaly alerts when a new target is added:
$$\text{Sample Count} < 10 \implies \text{is\_sufficient\_evidence} = \text{False}$$
Baseline-deviation anomaly rules (such as `HTTP_BASELINE_P95_EXCEEDED`) will **NOT** trigger until at least 10 valid samples are accumulated for that target.

---

## 5. Deterministic Diagnosis Categories

NetPath classifies root causes into 13 standardized engineering categories:

| Category | Affected Layer | Typical Symptoms |
| :--- | :--- | :--- |
| `DNS_FAILURE` | DNS | Hostname does not resolve; NXDOMAIN; DNS timeout. |
| `DNS_DEGRADATION` | DNS | DNS latency exceeds P95 or 300ms; lower layers nominal once resolved. |
| `TCP_CONNECTIVITY_FAILURE` | TCP | Connection refused; port blocked by firewall; host unreachable. |
| `TCP_DEGRADATION` | TCP | SYN-ACK connect latency exceeds baseline or 250ms. |
| `TLS_FAILURE` | TLS | Certificate invalid, hostname mismatch, or protocol mismatch. |
| `TLS_CERTIFICATE_EXPIRING` | TLS | Valid certificate expires within 30 days. |
| `HTTP_APPLICATION_ERROR` | HTTP | HTTP 500, 502, 503, 504, 404, or 429 returned by server. |
| `HTTP_APPLICATION_LATENCY` | HTTP | DNS/TCP/TLS nominal, but HTTP response exceeds P95; TTFB high. |
| `NETWORK_PACKET_LOSS` | Network | Hop timeouts, packet loss, TCP latency elevated simultaneously. |
| `NETWORK_LATENCY` | Network | Transit routing latency elevated across multiple intermediate hops. |
| `NETWORK_INTERFACE_ERRORS`| System | Local interface hardware drops or packet transmission errors. |
| `RESOURCE_PRESSURE` | System | Host CPU or memory saturated (> 90%). |
| `INSUFFICIENT_EVIDENCE` | None | All probed layers nominal or sample count insufficient. |

---

## 6. Database Design (MySQL 8)

The relational schema is implemented with SQLAlchemy 2.0 and PyMySQL:

```
[targets]
   ├── id (PK, INT)
   ├── url (VARCHAR, UNIQUE, INDEX)
   ├── hostname (VARCHAR, INDEX)
   ├── port, scheme, path
   └── created_at, updated_at

[diagnostic_sessions]
   ├── id (PK, VARCHAR UUID)
   ├── target_id (FK -> targets.id, CASCADE, INDEX)
   ├── correlation_id (VARCHAR, INDEX)
   ├── status (VARCHAR, INDEX)
   ├── started_at, completed_at, duration_ms
   └── error_message

[dns_results]          -> (FK -> diagnostic_sessions.id)
[tcp_results]          -> (FK -> diagnostic_sessions.id)
[tls_results]          -> (FK -> diagnostic_sessions.id)
[http_results]         -> (FK -> diagnostic_sessions.id)
[network_hops]         -> (FK -> diagnostic_sessions.id, INDEX)
[system_metrics]       -> (FK -> diagnostic_sessions.id)
[metric_samples]       -> (FK -> targets.id, INDEX on target_id & metric_name)
[anomalies]            -> (FK -> diagnostic_sessions.id, INDEX)
[diagnoses]            -> (FK -> diagnostic_sessions.id, UNIQUE, INDEX)
[diagnosis_evidence]   -> (FK -> diagnoses.id, INDEX)
[recommendations]      -> (FK -> diagnoses.id, INDEX)
[incident_events]      -> (FK -> diagnostic_sessions.id, INDEX)
```

---

## 7. Security Architecture & SSRF Protection

NetPath implements defense-in-depth against Server-Side Request Forgery (SSRF):
1. **URL Scheme Enforcement**: Only `http` and `https` schemes are accepted. Schemes like `file://`, `ftp://`, `gopher://` are rejected immediately.
2. **Network Subnet Filtering**: All target IPs (both direct IP inputs and resolved DNS records) are checked against reserved/private subnets:
   - Loopback (`127.0.0.0/8`, `::1`)
   - RFC 1918 Private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   - Link-local and Cloud Metadata (`169.254.0.0/16`, `fe80::/10`)
   - Broadcast and Multicast (`224.0.0.0/4`, `255.255.255.255`)
3. **Controlled Test Lab Allowlist**: To support safe testing against mock microservices inside Docker, an explicit environment setting `ALLOW_PRIVATE_IPS=true` or `ALLOWLISTED_HOSTS=["test-service-a", "test-service-b", "test-service-c"]` can be enabled.
4. **Subprocess Sanitization**: Network path traceroute arguments are strictly sanitized using regex `[^a-zA-Z0-9.\-:]` and invoked with `shell=False` and strict timeouts.
