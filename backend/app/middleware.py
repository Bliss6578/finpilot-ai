from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_metrics_lock = Lock()
_metrics = {
    "requests": 0,
    "server_errors": 0,
    "rate_limited": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}


def metrics_snapshot() -> dict:
    """Return process-level operational counters without tenant or request data."""
    with _metrics_lock:
        return dict(_metrics)


class SecurityAndRateLimitMiddleware(BaseHTTPMiddleware):
    """Small-instance rate protection; use Redis-backed limits when horizontally scaled."""

    def __init__(self, app, general_per_minute: int = 180, auth_per_minute: int = 12):
        super().__init__(app)
        self.general = general_per_minute
        self.auth = auth_per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        client = request.client.host if request.client else "unknown"
        sensitive = request.url.path.startswith("/api/auth/") or request.url.path.endswith("/chat")
        limit = self.auth if sensitive else self.general
        key = f"{client}:{'sensitive' if sensitive else 'general'}"
        now = monotonic()
        with self.lock:
            bucket = self.hits[key]
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                with _metrics_lock:
                    _metrics["rate_limited"] += 1
                return JSONResponse(status_code=429, content={"detail": "Too many requests. Please retry shortly.", "request_id": request_id}, headers={"Retry-After": "60", "X-Request-ID": request_id})
            bucket.append(now)
        with _metrics_lock:
            _metrics["requests"] += 1
        response = await call_next(request)
        if response.status_code >= 500:
            with _metrics_lock:
                _metrics["server_errors"] += 1
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
