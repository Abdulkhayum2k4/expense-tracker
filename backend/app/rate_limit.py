"""Per-IP rate limits for the auth endpoints (in memory: fine for a single API instance)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
