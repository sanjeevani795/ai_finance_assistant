"""Small retry helper for HTTP / flaky APIs."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    backoff_seconds: float,
    operation: str,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — surface to caller after retries
            last_exc = exc
            logger.warning("%s failed (attempt %s/%s): %s", operation, attempt, max_attempts, exc)
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)
    assert last_exc is not None
    raise last_exc
