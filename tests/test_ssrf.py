"""SSRF regression tests. DNS is mocked so the suite runs offline in CI."""

from __future__ import annotations

import os
import socket
from uuid import uuid4

import httpx
import pytest

os.environ.setdefault("CELERY_ALWAYS_EAGER", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AUTO_CREATE_DB", "true")

from app.validators import ssrf
from app.validators.ssrf import SSRFError, is_ssrf_url, resolve_public_ips, safe_request


def fake_dns(mapping: dict[str, list[str]]):
    """Return a getaddrinfo replacement that resolves hosts from *mapping*."""

    def _getaddrinfo(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(f"unknown host {host}")
        out = []
        for ip in mapping[host]:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
            out.append((family, socket.SOCK_STREAM, 6, "", sockaddr))
        return out

    return _getaddrinfo


# ── Layer 1: static checks (no DNS) ───────────────────────────────────────────

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost:8000/",
        "http://LOCALHOST/",
        "http://169.254.169.254/latest/meta-data/",   # cloud metadata
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",                  # IPv4-mapped IPv6
        "http://2130706433/",                          # decimal 127.0.0.1
        "http://0x7f000001/",                          # hex 127.0.0.1
        "http://127.1/",                               # short form
        "http://0177.0.0.1/",                          # octal
        "http://0/",                                   # 0.0.0.0
        "http://100.64.0.1/",                          # CGNAT, not caught by is_private
        "http://redis:6379/",                          # compose service
        "http://api.internal/",
        "http://printer.local/",
        "http://foo.localhost/",
        "http://metadata.google.internal/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "not a url",
        "http:///nohost",
    ],
)
def test_static_check_blocks(url):
    assert is_ssrf_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.github.com/",
        "http://example.com:8080/health?x=1",
        "https://8.8.8.8/",
        "https://[2606:4700:4700::1111]/",
    ],
)
def test_static_check_allows_public(url):
    assert not is_ssrf_url(url)


# ── Layer 2: DNS resolution ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "host, ips",
    [
        ("127.0.0.1.nip.io", ["127.0.0.1"]),            # wildcard DNS service
        ("localtest.me", ["127.0.0.1"]),
        ("evil.example", ["169.254.169.254"]),           # metadata via DNS
        ("v6.example", ["::1"]),
        ("mixed.example", ["93.184.216.34", "10.0.0.1"]),  # one bad record is enough
    ],
)
def test_dns_resolving_to_private_is_blocked(monkeypatch, host, ips):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({host: ips}))
    assert not is_ssrf_url(f"http://{host}/")  # passes the cheap check...
    with pytest.raises(SSRFError):              # ...but not the real one
        resolve_public_ips(f"http://{host}/")


def test_dns_public_is_allowed(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"api.example": ["93.184.216.34"]}))
    assert [str(a) for a in resolve_public_ips("https://api.example/")] == ["93.184.216.34"]


def test_unresolvable_host_is_blocked(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({}))
    with pytest.raises(SSRFError):
        resolve_public_ips("http://nope.example/")


# ── Pinning: we connect to the IP we validated ────────────────────────────────

def _capture_client(captured: dict, status: int = 200, headers: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["host_header"] = request.headers.get("host")
        captured["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(status, headers=headers or {}, json={"ok": True})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_request_is_pinned_to_validated_ip(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"api.example": ["93.184.216.34"]}))
    captured: dict = {}
    resp = safe_request(
        "GET", "https://api.example:8443/v1/health?x=1",
        timeout=5, headers={"Host": "spoofed.internal"}, client=_capture_client(captured),
    )
    assert resp.status_code == 200
    assert captured["url"] == "https://93.184.216.34:8443/v1/health?x=1"
    assert captured["host_header"] == "api.example:8443"   # caller cannot override Host
    assert captured["sni"] == "api.example"                # TLS cert still verified for the name


def test_ipv6_pinning_brackets_address(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"v6.example": ["2606:4700:4700::1111"]}))
    captured: dict = {}
    safe_request("GET", "http://v6.example/", timeout=5, client=_capture_client(captured))
    assert captured["url"] == "http://[2606:4700:4700::1111]/"
    assert captured["sni"] is None  # plain HTTP: no SNI


def test_dns_rebinding_cannot_swap_ip(monkeypatch):
    """A rebinding server answers public for the check and 127.0.0.1 afterwards.
    We resolve exactly once and connect to that IP, so the second answer is never used."""
    answers = iter([["93.184.216.34"], ["127.0.0.1"]])
    calls = {"n": 0}

    def rebinding(host, port, *a, **kw):
        calls["n"] += 1
        return fake_dns({host: next(answers)})(host, port)

    monkeypatch.setattr(ssrf.socket, "getaddrinfo", rebinding)
    captured: dict = {}
    safe_request("GET", "http://rebind.example/", timeout=5, client=_capture_client(captured))
    assert calls["n"] == 1
    assert captured["url"].startswith("http://93.184.216.34/")


def test_redirects_are_not_followed(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"api.example": ["93.184.216.34"]}))
    captured: dict = {}
    resp = safe_request(
        "GET", "http://api.example/", timeout=5,
        client=_capture_client(captured, status=302, headers={"Location": "http://169.254.169.254/"}),
    )
    assert resp.status_code == 302  # returned as-is, never followed
    assert "169.254" not in captured["url"]


# ── Worker + webhook integration ──────────────────────────────────────────────

def test_worker_records_fail_for_host_resolving_to_private(monkeypatch):
    from app.db.session import init_db
    from worker.tasks import execute_check

    init_db()
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"127.0.0.1.nip.io": ["127.0.0.1"]}))
    sent = []
    monkeypatch.setattr(httpx.Client, "request", lambda *a, **kw: sent.append(a) or None)

    result = execute_check({
        "id": str(uuid4()), "name": "rebind", "url": "http://127.0.0.1.nip.io/admin",
        "run_id": str(uuid4()),
    })
    assert result.status == "fail"
    assert result.error_message == "SSRF blocked: Invalid target"
    assert sent == []  # no request ever left the worker


def test_webhook_to_private_host_is_dropped_not_retried(monkeypatch):
    import alerts

    monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_dns({"hook.example": ["10.0.0.7"]}))
    sent = []
    monkeypatch.setattr(httpx.Client, "request", lambda *a, **kw: sent.append(a))
    alerts.dispatch_webhook.run("http://hook.example/alert", {"event": "DOWN"})  # must not raise
    assert sent == []
