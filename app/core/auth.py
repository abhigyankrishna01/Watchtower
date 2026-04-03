from __future__ import annotations

from typing import Optional

import jwt
from fastapi import Header, HTTPException, status

from app.core.config import settings


def _validate_jwt(token: str) -> None:
    try:
        jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
        )
    except jwt.PyJWTError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT") from exc


def require_auth(
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    api_key_enabled = bool(settings.api_auth_token)
    jwt_enabled = bool(settings.jwt_secret)

    if not api_key_enabled and not jwt_enabled:
        return

    if api_key_enabled and x_api_key == settings.api_auth_token:
        return

    if jwt_enabled and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            _validate_jwt(token)
            return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
