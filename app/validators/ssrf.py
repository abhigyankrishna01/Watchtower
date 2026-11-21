"""
SSRF (Server-Side Request Forgery) protection.

Two layers:
  1. API front door — ``is_ssrf_url``: fast string/IP checks with no DNS lookup,
     safe to call inside Pydantic validators.
  2. Worker, at request time — ``safe_request``: resolves DNS, rejects the URL if
     ANY resolved address is non-public, then connects to that exact IP
     (DNS pinning), so a rebinding DNS server cannot swap in 127.0.0.1 between
     the check and the connection.

Bypasses this module defends against (all covered in tests/test_ssrf.py):
  - Public hostnames that resolve to private IPs  (127.0.0.1.nip.io, localtest.me)
  - Legacy numeric IPv4 forms                      (2130706433, 0x7f000001, 127.1, 0177.0.0.1)
  - IPv4-mapped IPv6                               ([::ffff:127.0.0.1])
  - Non-global ranges Python's is_private misses   (100.64.0.0/10 CGNAT, etc.)
  - DNS rebinding between check and connect        (pinned connection)
  - Redirects to internal hosts                    (redirects are never followed)
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Exact hostnames that are always internal (case-insensitive).
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        # Docker Compose service names used in this project
        "redis",
        "db",
        "postgres",
        "worker",
        "beat",
        "app",
        "prometheus",
        "grafana",
        "frontend",
    }
)
# Internal-only DNS suffixes.
_BLOCKED_SUFFIXES: tuple[str, ...] = (".localhost", ".local", ".internal", ".lan", ".home.arpa")

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class SSRFError(ValueError):
    """Raised when a URL targets, or resolves to, a non-public address."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_blocked_ip(addr: IPAddress) -> bool:
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    # is_global is stricter than "not is_private": it also excludes CGNAT
    # (100.64.0.0/10), documentation ranges, benchmarking ranges, etc.
    return not addr.is_global or addr.is_multicast


def _parse_ip_literal(host: str) -> IPAddress | None:
    """Parse a host as an IP, including legacy IPv4 forms that OS resolvers accept
    (decimal 2130706433, hex 0x7f000001, short 127.1, octal 0177.0.0.1)."""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host))
    except (OSError, ValueError):
        return None


def _hostname_blocked(host: str) -> bool:
    host = host.lower().rstrip(".")
    return host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES)


# ── Layer 1: API front door (no DNS) ──────────────────────────────────────────

def is_ssrf_url(url: str) -> bool:
    """Return True if *url* is malformed, non-HTTP(S), or obviously internal.

    Does not resolve DNS (keeps Pydantic validation fast). Hostnames that
    resolve to private IPs are caught later by ``safe_request``.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return True

    if parts.scheme.lower() not in ALLOWED_SCHEMES or not host:
        return True
    if _hostname_blocked(host):
        return True

    addr = _parse_ip_literal(host)
    return addr is not None and _is_blocked_ip(addr)


# ── Layer 2: request time (DNS + pinning) ─────────────────────────────────────

def resolve_public_ips(url: str) -> list[IPAddress]:
    """Resolve the URL's host and return its addresses.

    Raises SSRFError if the URL fails the static checks or if ANY resolved
    address is non-public. (Checking only the first address would let an
    attacker return [public, 127.0.0.1] and hope the client picks the second.)
    """
    if is_ssrf_url(url):
        raise SSRFError("URL targets an internal or non-HTTP address")

    parts = urlsplit(url)
    host = parts.hostname
    assert host is not None  # guaranteed by is_ssrf_url
    port = parts.port or (443 if parts.scheme == "https" else 80)

    literal = _parse_ip_literal(host)
    if literal is not None:
        return [literal]

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFError(f"DNS resolution failed for {host}") from exc

    addrs: list[IPAddress] = []
    for *_, sockaddr in infos:
        addr = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])  # drop IPv6 zone id
        if _is_blocked_ip(addr):
            raise SSRFError(f"{host} resolves to a non-public address")
        if addr not in addrs:
            addrs.append(addr)
    if not addrs:
        raise SSRFError(f"{host} did not resolve to any address")
    return addrs


def _pinned_url(url: str, ip: IPAddress) -> str:
    parts = urlsplit(url)
    ip_host = f"[{ip}]" if ip.version == 6 else str(ip)
    netloc = f"{ip_host}:{parts.port}" if parts.port else ip_host
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))


def safe_request(
    method: str,
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    json: Any = None,
    client: httpx.Client | None = None,
) -> httpx.Response:
    """Make an HTTP request that cannot reach internal addresses.

    Resolves and validates DNS once, then connects to the validated IP while
    keeping the original Host header and TLS SNI, so virtual hosting and
    certificate verification still work. Redirects are never followed:
    a 30x to an internal host would otherwise bypass every check above.
    """
    ip = resolve_public_ips(url)[0]
    parts = urlsplit(url)
    host = parts.hostname
    assert host is not None

    req_headers = {k: v for k, v in (headers or {}).items() if k.lower() != "host"}
    req_headers["Host"] = parts.netloc.rsplit("@", 1)[-1]  # host[:port], no userinfo

    extensions = {"sni_hostname": host} if parts.scheme == "https" else {}

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False)
    try:
        return client.request(
            method,
            _pinned_url(url, ip),
            headers=req_headers,
            json=json,
            extensions=extensions,
            follow_redirects=False,
        )
    finally:
        if owns_client:
            client.close()
