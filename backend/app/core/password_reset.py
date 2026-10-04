import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque

from backend.app.config import get_settings

settings = get_settings()

# 32 random bytes -> 43 URL-safe characters (256 bits of entropy).
_TOKEN_BYTES = 32


def generate_reset_token() -> str:
    """Generate an unpredictable, URL-safe password reset token."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_reset_token(token: str) -> str:
    """
    Hash a reset token for storage and lookup.

    A fast hash is appropriate here (unlike passwords or 6-digit OTPs)
    because the token carries 256 bits of entropy and cannot be guessed;
    it also lets the token be found with an indexed equality lookup.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def frontend_base_url() -> str | None:
    """
    Base URL used in emailed links. Never derived from request headers,
    which an attacker could forge to point the link at their own site.
    """
    if settings.FRONTEND_BASE_URL:
        return settings.FRONTEND_BASE_URL.rstrip("/")

    if settings.APP_ENV == "development" and settings.CORS_ORIGINS:
        return settings.CORS_ORIGINS[0].rstrip("/")

    return None


def build_reset_link(token: str) -> str | None:
    """
    Build the frontend reset link. The token goes in the URL fragment, which
    browsers never send to servers or include in Referer headers.
    """
    base_url = frontend_base_url()

    if not base_url:
        return None

    path = "/" + settings.FRONTEND_RESET_PASSWORD_PATH.lstrip("/")

    return f"{base_url}{path}#token={token}"


class SlidingWindowRateLimiter:
    """
    Minimal in-process sliding-window limiter keyed by client IP.

    State lives in this process only: it resets on restart and is not
    shared between multiple workers. The per-account limits stored in the
    database are the durable protection against email flooding.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            hits = self._hits[key]

            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self.max_requests:
                return False

            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


forgot_password_ip_limiter = SlidingWindowRateLimiter(
    max_requests=settings.PASSWORD_RESET_IP_MAX_REQUESTS,
    window_seconds=settings.PASSWORD_RESET_IP_WINDOW_SECONDS,
)
