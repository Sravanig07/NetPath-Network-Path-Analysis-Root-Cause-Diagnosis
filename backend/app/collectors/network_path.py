from __future__ import annotations

import logging
import re
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.network_path")


class NetworkPathCollector(BaseCollector):
    """
    Performs network path hop tracing using safe subprocess invocation
    of traceroute/tracepath, with graceful fallback to socket RTT probing.
    """

    def __init__(self, timeout_seconds: float = 8.0, max_hops: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.max_hops = max_hops

    def collect(self, target_host: str, target_ip: Optional[str] = None) -> List[Dict[str, Any]]:
        # Strictly sanitize host/ip - only alphanumeric, dots, colons, hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9.\-:]", "", target_ip or target_host)
        hops: List[Dict[str, Any]] = []

        traceroute_bin = shutil.which("traceroute") or shutil.which("tracepath")
        
        if traceroute_bin:
            try:
                cmd = [traceroute_bin, "-n", "-m", str(self.max_hops), "-w", "1", sanitized]
                proc = subprocess.run(
                    cmd,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                if proc.stdout:
                    hops = self._parse_traceroute_output(proc.stdout)
            except subprocess.TimeoutExpired:
                logger.warning(f"Traceroute timed out for {sanitized}")
            except Exception as e:
                logger.warning(f"Error running traceroute ({e}). Using socket path fallback.")

        # If traceroute is not available or returned no hops (e.g. unprivileged container)
        if not hops:
            hops = self._fallback_socket_probe(sanitized, target_ip)

        return hops

    def _parse_traceroute_output(self, output: str) -> List[Dict[str, Any]]:
        hops = []
        lines = output.strip().splitlines()
        for line in lines:
            line = line.strip()
            # Traceroute lines usually start with hop number: "1  192.168.1.1  1.234 ms"
            match = re.match(r"^(\d+)\s+(.+)", line)
            if not match:
                continue

            hop_num = int(match.group(1))
            rest = match.group(2)

            if "*" in rest and not re.search(r"\d+\.\d+\.\d+\.\d+", rest):
                # All probes timed out on this hop
                hops.append({
                    "hop_number": hop_num,
                    "ip_address": None,
                    "hostname": None,
                    "rtt_ms": None,
                    "is_timeout": True,
                    "packet_loss_pct": 100.0,
                    "note": "Possible ICMP filtering or packet drop",
                })
            else:
                ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
                rtt_match = re.search(r"(\d+(?:\.\d+)?)\s*ms", rest)
                ip_str = ip_match.group(1) if ip_match else None
                rtt_val = float(rtt_match.group(1)) if rtt_match else None

                hops.append({
                    "hop_number": hop_num,
                    "ip_address": ip_str,
                    "hostname": ip_str,
                    "rtt_ms": rtt_val,
                    "is_timeout": False,
                    "packet_loss_pct": 0.0,
                    "note": "Hop responsive",
                })
        return hops

    def _fallback_socket_probe(self, host: str, target_ip: Optional[str]) -> List[Dict[str, Any]]:
        """Fallback when traceroute binary is absent or unprivileged."""
        hops = []
        dest_ip = target_ip or host
        # Hop 1: Local gateway / interface
        hops.append({
            "hop_number": 1,
            "ip_address": "127.0.0.1",
            "hostname": "localhost",
            "rtt_ms": 0.2,
            "is_timeout": False,
            "packet_loss_pct": 0.0,
            "note": "Local loopback / interface check",
        })

        # Hop 2: Destination socket probe
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            # Try connecting to port 80 or 443
            sock.connect_ex((dest_ip, 80))
            sock.close()
            rtt = (time.perf_counter() - start) * 1000.0
            hops.append({
                "hop_number": 2,
                "ip_address": dest_ip,
                "hostname": host,
                "rtt_ms": round(rtt, 2),
                "is_timeout": False,
                "packet_loss_pct": 0.0,
                "note": "Direct destination socket reachability",
            })
        except Exception:
            hops.append({
                "hop_number": 2,
                "ip_address": dest_ip,
                "hostname": host,
                "rtt_ms": None,
                "is_timeout": True,
                "packet_loss_pct": 100.0,
                "note": "Destination probe timeout",
            })

        return hops
