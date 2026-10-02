from __future__ import annotations

import errno
import logging
import socket
import time
from typing import Any, Dict, Optional

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.tcp")


class TcpCollector(BaseCollector):
    """
    Measures TCP connection handshake timing and connectivity state
    to a destination IP and port.
    """

    def __init__(self, timeout_seconds: float = 5.0, degradation_threshold_ms: float = 250.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.degradation_threshold_ms = degradation_threshold_ms

    def collect(self, destination_ip: str, destination_port: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "destination_ip": destination_ip,
            "destination_port": destination_port,
            "connect_latency_ms": 0.0,
            "status": "SUCCESS",
            "error_message": None,
        }

        # Determine address family (IPv4 vs IPv6)
        family = socket.AF_INET6 if ":" in destination_ip else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout_seconds)

        start_time = time.perf_counter()
        try:
            sock.connect((destination_ip, destination_port))
            connect_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["connect_latency_ms"] = round(connect_duration_ms, 2)

            if connect_duration_ms > self.degradation_threshold_ms:
                result["status"] = "TCP_DEGRADATION"
                result["error_message"] = (
                    f"TCP handshake latency ({connect_duration_ms:.1f}ms) "
                    f"exceeded threshold ({self.degradation_threshold_ms:.1f}ms)"
                )
            else:
                result["status"] = "SUCCESS"

        except socket.timeout:
            connect_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["connect_latency_ms"] = round(connect_duration_ms, 2)
            result["status"] = "TCP_CONNECTIVITY_FAILURE"
            result["error_message"] = f"TCP connection timed out after {self.timeout_seconds}s"

        except ConnectionRefusedError:
            connect_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["connect_latency_ms"] = round(connect_duration_ms, 2)
            result["status"] = "TCP_CONNECTIVITY_FAILURE"
            result["error_message"] = f"Connection refused on port {destination_port}"

        except OSError as e:
            connect_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["connect_latency_ms"] = round(connect_duration_ms, 2)
            result["status"] = "TCP_CONNECTIVITY_FAILURE"
            if e.errno == errno.ENETUNREACH:
                result["error_message"] = "Network unreachable"
            elif e.errno == errno.EHOSTUNREACH:
                result["error_message"] = "Host unreachable"
            else:
                result["error_message"] = f"TCP socket error: {e.strerror or str(e)}"

        except Exception as ex:
            connect_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result["connect_latency_ms"] = round(connect_duration_ms, 2)
            result["status"] = "TCP_CONNECTIVITY_FAILURE"
            result["error_message"] = f"TCP handshake failed: {str(ex)}"

        finally:
            try:
                sock.close()
            except Exception:
                pass

        return result
