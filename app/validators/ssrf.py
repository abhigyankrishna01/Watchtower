"""
SSRF (Server-Side Request Forgery) protection utilities.

Used at two layers:
  1. API front-door (Pydantic field_validator) — fast string/IP checks, no DNS.
  2. Worker defence-in-depth (execute_check) — re-validates just before HTTPX fires.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# Hostnames that are always internal — exact match, case-insensitive.
# Covers loopback aliases and Docker Compose service names used in this project.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        # Docker Compose service names
        "redis",
        "db",
        "postgres",
        "worker",
        "beat",
        "app",
    }
)


def is_ssrf_url(url: str) -> bool:
    """
    Return True if *url* targets an internal or private host.

    Checks (in order):
    - Malformed / missing hostname → blocked
    - Hostname in _BLOCKED_HOSTNAMES → blocked
    - Hostname is a valid IP address that falls in a private/loopback/
      link-local/reserved/multicast/unspecified range → blocked
    - Otherwise → allowed (hostname DNS resolution is intentionally deferred
      to avoid latency inside Pydantic validators)
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname  # lowercased; IPv6 brackets stripped automatically
    except Exception:
        return True  # unparseable URL — treat as unsafe

    if not host:
        return True

    if host.lower() in _BLOCKED_HOSTNAMES:
        return True

    # If the host is a bare IP address, check whether it's private.
    try:
        addr = ipaddress.ip_address(host)
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            return True
    except ValueError:
        pass  # Not an IP address — a plain hostname, allow through

    return False
