from __future__ import annotations

from typing import List
from backend.app.schemas.analysis import RecommendationSchema


class RecommendationEngine:
    """Generates deterministic, highly actionable remediation steps based on root-cause category."""

    def generate(self, category: str, affected_layer: str, summary: str) -> List[RecommendationSchema]:
        recommendations_map = {
            "DNS_FAILURE": [
                "Verify hostname syntax and check domain registration status.",
                "Inspect local resolver configuration (/etc/resolv.conf) and test upstream resolver reachability.",
                "Execute diagnostic query against alternate public resolvers: dig @8.8.8.8 <host> +trace",
                "Inspect DNS authoritative nameserver health and zone delegation status."
            ],
            "DNS_DEGRADATION": [
                "Benchmark latency against alternate DNS resolvers (e.g. 1.1.1.1, 8.8.8.8).",
                "Enable or check local DNS caching daemon (systemd-resolved, nscd, dnsmasq).",
                "Inspect recursive resolver query times and TTL configurations to improve caching efficiency."
            ],
            "TCP_CONNECTIVITY_FAILURE": [
                "Verify target daemon is active and listening on target port: ss -tulpn | grep :<port>",
                "Inspect host firewall rules (iptables, nftables, ufw) and cloud security group ACLs.",
                "Check intermediate NAT gateways, firewalls, and route table definitions between source and destination."
            ],
            "TCP_DEGRADATION": [
                "Inspect TCP retransmissions and segment drop counters: ss -s or netstat -s",
                "Verify server SYN backlog queue depth and listen queue settings: sysctl net.ipv4.tcp_max_syn_backlog",
                "Compare RTT variance across intermediate hops using network path tracer."
            ],
            "TLS_FAILURE": [
                "Inspect remote certificate chain using OpenSSL: openssl s_client -connect <host>:<port> -servername <host>",
                "Ensure target certificate Subject Alternative Name (SAN) matches the target hostname.",
                "Check server cipher suite configuration and minimum supported TLS protocol versions (TLSv1.2, TLSv1.3)."
            ],
            "TLS_CERTIFICATE_EXPIRING": [
                "Trigger immediate SSL/TLS certificate renewal before expiration window closes.",
                "Inspect automated renewal daemon logs (e.g. Certbot, AWS ACM, HashiCorp Vault).",
                "Verify that renewed certificate has been reloaded into the active web server process."
            ],
            "HTTP_APPLICATION_ERROR": [
                "Inspect web application backend logs and error traces around the incident timestamp.",
                "Review reverse proxy / load balancer error logs (Nginx / Envoy / ALB 5xx logs).",
                "Verify backend database connectivity, active connection pool limits, and queue timeouts."
            ],
            "HTTP_APPLICATION_LATENCY": [
                "Inspect application APM distributed traces for slow database queries or remote RPC calls.",
                "Review application worker thread/process pool utilization and request queue depth.",
                "Check for database connection pool exhaustion or unindexed database queries.",
                "Compare server Time-To-First-Byte (TTFB) against raw content transfer time."
            ],
            "NETWORK_PACKET_LOSS": [
                "Inspect intermediate hops exhibiting packet loss using hop traceroute data.",
                "Check with network provider for route flapping, transit congestion, or BGP updates.",
                "Verify MTU configuration and check for Path MTU Discovery (PMTUD) black holes."
            ],
            "NETWORK_INTERFACE_ERRORS": [
                "Check detailed interface packet statistics: ip -s link show",
                "Inspect host socket buffer memory limits: sysctl net.core.rmem_max net.core.wmem_max",
                "Check physical switch port duplex settings or virtual NIC driver drop counters."
            ],
            "RESOURCE_PRESSURE": [
                "Identify top CPU and memory consuming processes: ps aux --sort=-%cpu | head -n 10",
                "Verify whether container CPU quotas (cgroups) are throttled: cat /sys/fs/cgroup/cpu.stat",
                "Scale out application worker replicas or augment instance compute capacity."
            ],
            "INSUFFICIENT_EVIDENCE": [
                "Allow diagnostic poller to collect at least 10 baseline samples for this target.",
                "All probed network layers are currently operating within nominal parameters."
            ]
        }

        action_strings = recommendations_map.get(category, recommendations_map["INSUFFICIENT_EVIDENCE"])
        return [
            RecommendationSchema(action_order=idx + 1, action_text=text)
            for idx, text in enumerate(action_strings)
        ]
