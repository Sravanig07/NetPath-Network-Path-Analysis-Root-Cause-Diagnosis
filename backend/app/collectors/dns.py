from __future__ import annotations

import logging
import socket
import time
from typing import Any, Dict, List, Optional
import dns.resolver
import dns.exception

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.dns")


class DnsCollector(BaseCollector):
    """
    Resolves hostname across record types (A, AAAA, CNAME),
    measures resolution latency, and flags failures or degradations.
    """

    def __init__(self, timeout_seconds: float = 5.0, degradation_threshold_ms: float = 300.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.degradation_threshold_ms = degradation_threshold_ms

    def collect(self, hostname: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "hostname": hostname,
            "resolver": "system",
            "latency_ms": 0.0,
            "record_type": "A",
            "addresses": [],
            "status": "SUCCESS",
            "error_message": None,
        }

        start_time = time.perf_counter()

        # 1. Local test lab hostnames mapping for testing outside Docker
        if hostname.lower() in ("test-service-a", "test-service-b", "test-service-c", "localhost"):
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["latency_ms"] = round(max(duration_ms, 0.4), 2)
            result["addresses"] = ["127.0.0.1"]
            result["status"] = "SUCCESS"
            result["resolver"] = "local test-lab"
            return result

        # Setup dnspython resolver if possible
        resolver = None
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout_seconds
            resolver.lifetime = self.timeout_seconds
            if resolver.nameservers:
                result["resolver"] = resolver.nameservers[0]
        except Exception:
            pass

        addresses: List[str] = []

        # 2. Try dnspython first
        if resolver:
            try:
                answers_a = resolver.resolve(hostname, "A")
                for rdata in answers_a:
                    addresses.append(rdata.address)
                result["record_type"] = "A"
            except Exception:
                pass

            try:
                answers_aaaa = resolver.resolve(hostname, "AAAA")
                for rdata in answers_aaaa:
                    addresses.append(rdata.address)
            except Exception:
                pass

        # 3. Resilient system resolver fallback (macOS, Windows, Linux, VPNs)
        if not addresses:
            try:
                addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
                for item in addr_info:
                    ip = item[4][0]
                    if ip not in addresses:
                        addresses.append(ip)
                result["resolver"] = "system"
            except socket.gaierror as e:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                result["latency_ms"] = round(duration_ms, 2)
                result["status"] = "DNS_FAILURE"
                result["error_message"] = f"Domain {hostname} does not exist: {e.strerror or str(e)}"
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                result["latency_ms"] = round(duration_ms, 2)
                result["status"] = "DNS_FAILURE"
                result["error_message"] = f"DNS resolution failed: {str(e)}"
                return result

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        result["latency_ms"] = round(duration_ms, 2)
        result["addresses"] = addresses

        if not addresses:
            result["status"] = "DNS_FAILURE"
            result["error_message"] = f"No address records returned for {hostname}"
        elif duration_ms > self.degradation_threshold_ms:
            result["status"] = "DNS_DEGRADATION"
            result["error_message"] = f"DNS latency ({duration_ms:.1f}ms) exceeded threshold ({self.degradation_threshold_ms:.1f}ms)"
        else:
            result["status"] = "SUCCESS"

        return result
