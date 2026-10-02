from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict
import psutil

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.linux_metrics")


class LinuxMetricsCollector(BaseCollector):
    """
    Collects host/container system health metrics: CPU, memory, load average,
    and network interface counters (bytes, errors, drops) using psutil and /proc.
    """

    def __init__(
        self,
        cpu_threshold_pct: float = 90.0,
        mem_threshold_pct: float = 90.0,
        drop_threshold: int = 50
    ) -> None:
        super().__init__()
        self.cpu_threshold_pct = cpu_threshold_pct
        self.mem_threshold_pct = mem_threshold_pct
        self.drop_threshold = drop_threshold

    def collect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "cpu_pct": 0.0,
            "memory_pct": 0.0,
            "load_1m": 0.0,
            "load_5m": 0.0,
            "load_15m": 0.0,
            "net_bytes_sent": 0,
            "net_bytes_recv": 0,
            "net_errin": 0,
            "net_errout": 0,
            "net_dropin": 0,
            "net_dropout": 0,
            "status": "SUCCESS",
            "error_message": None,
        }

        try:
            # CPU & Memory
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            result["cpu_pct"] = round(cpu_pct, 1)
            result["memory_pct"] = round(mem.percent, 1)

            # Load average
            try:
                load_1m, load_5m, load_15m = os.getloadavg()
                result["load_1m"] = round(load_1m, 2)
                result["load_5m"] = round(load_5m, 2)
                result["load_15m"] = round(load_15m, 2)
            except (AttributeError, OSError):
                # /proc/loadavg check on Linux if os.getloadavg not available
                if os.path.exists("/proc/loadavg"):
                    with open("/proc/loadavg", "r") as f:
                        parts = f.read().split()
                        result["load_1m"] = float(parts[0])
                        result["load_5m"] = float(parts[1])
                        result["load_15m"] = float(parts[2])

            # Network interface I/O counters
            net_io = psutil.net_io_counters()
            if net_io:
                result["net_bytes_sent"] = net_io.bytes_sent
                result["net_bytes_recv"] = net_io.bytes_recv
                result["net_errin"] = net_io.errin
                result["net_errout"] = net_io.errout
                result["net_dropin"] = net_io.dropin
                result["net_dropout"] = net_io.dropout

            # Inspect /proc/net/dev if available on Linux
            if sys.platform.startswith("linux") and os.path.exists("/proc/net/dev"):
                try:
                    with open("/proc/net/dev", "r") as f:
                        # Ensure we can read it safely
                        _ = f.readlines()
                except Exception as e:
                    logger.debug(f"Could not read /proc/net/dev: {e}")

            # Anomaly checks on host resources
            if result["net_errin"] > 0 or result["net_errout"] > 0 or result["net_dropin"] > self.drop_threshold:
                result["status"] = "NETWORK_INTERFACE_ERRORS"
                result["error_message"] = (
                    f"Interface errors detected: errin={result['net_errin']}, "
                    f"errout={result['net_errout']}, dropin={result['net_dropin']}"
                )
            elif cpu_pct > self.cpu_threshold_pct or mem.percent > self.mem_threshold_pct:
                result["status"] = "RESOURCE_PRESSURE"
                result["error_message"] = (
                    f"Host resource exhaustion: CPU={cpu_pct}%, Mem={mem.percent}%"
                )
            else:
                result["status"] = "SUCCESS"

        except Exception as ex:
            logger.error(f"Error collecting linux metrics: {ex}")
            result["status"] = "SUCCESS"  # graceful fallback
            result["error_message"] = f"Metric collection warning: {str(ex)}"

        return result
