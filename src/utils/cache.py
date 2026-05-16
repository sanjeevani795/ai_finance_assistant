"""Simple TTL cache for API responses."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            ts, val = item
            if now - ts > self._ttl:
                del self._data[key]
                logger.debug("TTL cache expired: %s", key)
                return None
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic(), value)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        hit = self.get(key)
        if hit is not None:
            return hit  # type: ignore[return-value]
        val = factory()
        self.set(key, val)
        return val
