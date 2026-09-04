"""
Lightweight in-memory sliding-window rate limiter for CartMind (TRD.md §11).
Prevents runaway LLM inference costs and API abuse during judging.
"""

import time
import threading
from typing import Dict, List
from fastapi import HTTPException, status, Request


class InMemoryRateLimiter:
    """
    Thread-safe sliding-window rate limiter.
    Stores list of UNIX timestamps per key (session_id or IP).
    """

    def __init__(self, requests_per_minute: int = 15, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._records: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """
        Validates whether the key has exceeded requests_per_minute.
        Raises HTTP 429 Too Many Requests if the limit is exceeded.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._records.get(key, [])
            # Evict timestamps outside the window
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.requests_per_minute:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: maximum {self.requests_per_minute} messages per minute. "
                        f"Please wait {retry_after} second(s) before sending another message."
                    ),
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            timestamps.append(now)
            self._records[key] = timestamps

    def reset(self, key: str = None) -> None:
        """Resets rate limit records (useful for unit testing)."""
        with self._lock:
            if key:
                self._records.pop(key, None)
            else:
                self._records.clear()


# Default instance: 15 messages per minute per session
chat_rate_limiter = InMemoryRateLimiter(requests_per_minute=15, window_seconds=60)
