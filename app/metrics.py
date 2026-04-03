from __future__ import annotations

from prometheus_client import Counter, Histogram

CHECK_REQUESTS = Counter(
    "watchtower_check_requests_total",
    "Total number of API checks performed",
    ["monitor_id", "status"],
)

CHECK_LATENCY = Histogram(
    "watchtower_check_latency_seconds",
    "Latency of API checks in seconds",
    ["monitor_id"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)

VALIDATION_FAILURES = Counter(
    "watchtower_validation_failures_total",
    "Total number of validation failures",
    ["monitor_id", "rule"],
)
