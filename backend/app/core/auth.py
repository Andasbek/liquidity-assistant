# backend/app/core/auth.py
from fastapi import Header, HTTPException
from typing import Iterable, Optional
from . import config

def require_any(*roles):
    allowed = set(roles)
    default_role = getattr(config, "DEFAULT_ROLE", None) or "Analyst"
    async def _inner(x_role: str | None = Header(default=None, alias="X-Role")):
        role = x_role or default_role
        if role not in allowed:
            raise HTTPException(403, "forbidden")
    return _inner
