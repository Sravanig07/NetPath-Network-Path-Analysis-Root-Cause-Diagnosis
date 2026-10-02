from __future__ import annotations

import datetime
import logging
import socket
import ssl
import time
from typing import Any, Dict, Optional, Tuple

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.tls")


class TlsCollector(BaseCollector):
    """
    Performs TLS handshake negotiation, inspects certificate validity,
    measures handshake latency, and detects expiration or cipher issues.
    """

    def __init__(self, timeout_seconds: float = 5.0, exp_warning_days: int = 30) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.exp_warning_days = exp_warning_days

    def collect(self, hostname: str, destination_ip: str, port: int = 443) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "tls_version": None,
            "cipher": None,
            "cert_subject": None,
            "cert_issuer": None,
            "cert_expires_at": None,
            "days_to_expiration": None,
            "handshake_latency_ms": 0.0,
            "is_valid": False,
            "status": "SUCCESS",
            "error_message": None,
        }

        # Create standard SSLContext with strict validation
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        start_time = time.perf_counter()
        raw_sock = None
        ssl_sock = None

        try:
            family = socket.AF_INET6 if ":" in destination_ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(self.timeout_seconds)
            raw_sock.connect((destination_ip, port))

            # Perform TLS wrap and handshake
            ssl_sock = context.wrap_socket(raw_sock, server_hostname=hostname)
            handshake_ms = (time.perf_counter() - start_time) * 1000.0
            result["handshake_latency_ms"] = round(handshake_ms, 2)
            result["tls_version"] = ssl_sock.version()
            cipher_info = ssl_sock.cipher()
            if cipher_info:
                result["cipher"] = cipher_info[0]

            cert = ssl_sock.getpeercert()
            if cert:
                result["is_valid"] = True
                # Parse subject & issuer
                subject_parts = [f"{k}={v}" for item in cert.get("subject", ()) for k, v in item]
                issuer_parts = [f"{k}={v}" for item in cert.get("issuer", ()) for k, v in item]
                result["cert_subject"] = ", ".join(subject_parts) or hostname
                result["cert_issuer"] = ", ".join(issuer_parts) or "Unknown Issuer"

                # Parse notAfter expiration
                not_after_str = cert.get("notAfter")
                if not_after_str:
                    # Format: 'May  9 12:00:00 2026 GMT'
                    try:
                        exp_dt = datetime.datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                        result["cert_expires_at"] = exp_dt
                        days_left = (exp_dt - datetime.datetime.utcnow()).days
                        result["days_to_expiration"] = days_left

                        if days_left <= 0:
                            result["is_valid"] = False
                            result["status"] = "TLS_FAILURE"
                            result["error_message"] = f"SSL Certificate expired {abs(days_left)} days ago"
                        elif days_left < self.exp_warning_days:
                            result["status"] = "TLS_CERTIFICATE_EXPIRING"
                            result["error_message"] = (
                                f"SSL Certificate expires soon ({days_left} days left, "
                                f"threshold: {self.exp_warning_days} days)"
                            )
                        else:
                            result["status"] = "SUCCESS"
                    except Exception as e:
                        logger.warning(f"Could not parse notAfter date '{not_after_str}': {e}")
                        result["status"] = "SUCCESS"
            else:
                result["status"] = "TLS_FAILURE"
                result["error_message"] = "No peer certificate returned"

        except ssl.SSLCertVerificationError as e:
            handshake_ms = (time.perf_counter() - start_time) * 1000.0
            result["handshake_latency_ms"] = round(handshake_ms, 2)
            result["is_valid"] = False
            result["status"] = "TLS_FAILURE"
            result["error_message"] = f"TLS Certificate verification failed: {e.verify_message}"

        except ssl.SSLError as e:
            handshake_ms = (time.perf_counter() - start_time) * 1000.0
            result["handshake_latency_ms"] = round(handshake_ms, 2)
            result["is_valid"] = False
            result["status"] = "TLS_FAILURE"
            result["error_message"] = f"TLS handshake negotiation error: {str(e)}"

        except socket.timeout:
            handshake_ms = (time.perf_counter() - start_time) * 1000.0
            result["handshake_latency_ms"] = round(handshake_ms, 2)
            result["status"] = "TLS_FAILURE"
            result["error_message"] = f"TLS handshake timed out after {self.timeout_seconds}s"

        except Exception as ex:
            handshake_ms = (time.perf_counter() - start_time) * 1000.0
            result["handshake_latency_ms"] = round(handshake_ms, 2)
            result["status"] = "TLS_FAILURE"
            result["error_message"] = f"TLS connection failed: {str(ex)}"

        finally:
            if ssl_sock:
                try:
                    ssl_sock.close()
                except Exception:
                    pass
            elif raw_sock:
                try:
                    raw_sock.close()
                except Exception:
                    pass

        return result
