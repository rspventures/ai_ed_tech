"""
Rate limiting (Phase 0).

A single shared slowapi Limiter keyed by client IP. A global default limit is
applied to every route via SlowAPIMiddleware (see app.main); sensitive routes
(auth, paid AI endpoints) add tighter per-route limits with the @limiter.limit
decorator, which requires a `request: Request` parameter in the endpoint.

Storage is in-memory by default (fine for a single worker). Set
RATE_LIMIT_STORAGE_URI to a redis:// URL for multi-worker deployments.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI or "memory://",
    headers_enabled=True,
)
