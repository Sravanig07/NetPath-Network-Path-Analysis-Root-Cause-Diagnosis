from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, List, Optional
from backend.app.config import settings


# Forbidden IP networks according to RFC 1918, RFC 3927, RFC 6890, etc.
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network Interconnect Device Benchmark
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


class SSRFValidationError(ValueError):
    """Raised when a URL violates SSRF or security constraints."""
    pass


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address falls within blocked/private/reserved subnets."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return True
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return True


def validate_and_parse_url(
    url: str,
    allow_private_ips: Optional[bool] = None,
    allowlisted_hosts: Optional[List[str]] = None
) -> Tuple[str, str, int, str]:
    """
    Validates target URL against SSRF and syntax rules.
    Returns: (scheme, hostname, port, path)
    Raises SSRFValidationError if invalid.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL cannot be empty.")

    clean_url = url.strip()
    if "://" in clean_url:
        scheme_prefix = clean_url.split("://")[0].lower()
        if scheme_prefix not in ("http", "https"):
            raise SSRFValidationError(f"Unsupported protocol scheme '{scheme_prefix}'. Only http and https are allowed.")
    else:
        clean_url = f"https://{clean_url}"

    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise SSRFValidationError(f"Unsupported protocol scheme '{scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("Target URL must contain a valid hostname.")

    hostname_lower = hostname.lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    if not (1 <= port <= 65535):
        raise SSRFValidationError(f"Invalid port number {port}. Port must be between 1 and 65535.")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    # Check test lab allowlist
    effective_allow_private = (
        allow_private_ips if allow_private_ips is not None else settings.ALLOW_PRIVATE_IPS
    )
    effective_allowlist = (
        allowlisted_hosts if allowlisted_hosts is not None else settings.ALLOWLISTED_HOSTS
    )

    if (
        effective_allow_private
        or hostname_lower in [h.lower() for h in effective_allowlist]
        or (hostname_lower in ("localhost", "127.0.0.1") and port in (8001, 8002, 8003))
    ):
        return scheme, hostname_lower, port, path

    # Check if host is direct IP
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if is_ip_blocked(str(ip)):
            raise SSRFValidationError(f"Access to private/restricted IP '{ip}' is blocked.")
        return scheme, hostname_lower, port, path
    except ValueError:
        # Not a raw IP literal, it is a DNS hostname
        pass

    # Block well-known local aliases
    if hostname_lower in ("localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"):
        raise SSRFValidationError(f"Access to local hostname '{hostname_lower}' is blocked.")

    # Resolve hostname to check all target IPs for DNS rebinding/SSRF
    try:
        addr_info = socket.getaddrinfo(hostname_lower, port, proto=socket.IPPROTO_TCP)
        resolved_ips = {item[4][0] for item in addr_info}
        if not resolved_ips:
            raise SSRFValidationError(f"Could not resolve hostname '{hostname_lower}'.")

        for ip_candidate in resolved_ips:
            if is_ip_blocked(ip_candidate):
                raise SSRFValidationError(
                    f"Hostname '{hostname_lower}' resolves to restricted IP '{ip_candidate}'."
                )
    except socket.gaierror as e:
        # DNS resolution failure will be handled by the DNS collector in diagnostics,
        # but if we cannot resolve it here, we allow the diagnostic workflow to run
        # so it accurately diagnoses DNS_FAILURE.
        pass

    return scheme, hostname_lower, port, path
