from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def _rate_limit_key(request: Request) -> str:
    """
    Identify the caller for rate limiting.
    Reads request.state.user_id stamped by get_current_user — so the limit
    is per-tenant, not per-IP. Falls back to IP for unauthenticated routes
    (e.g. /health).
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    if request.client:
        return f"ip:{request.client.host}"
    return "ip:unknown"


limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=settings.rate_limit_redis_url,
    default_limits=["60/minute"],
)
