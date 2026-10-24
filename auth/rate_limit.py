"""Small in-process login throttle suitable for the localhost MVP."""

from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic


WINDOW_SECONDS = 15 * 60
MAX_FAILURES = 5
MAX_TRACKED_CLIENTS = 2048
_failures: dict[str, deque[float]] = {}
_lock = Lock()


def login_retry_after(client_key: str, now: float | None = None) -> int | None:
    """Return seconds until another login attempt is allowed, or None."""
    current = monotonic() if now is None else now
    with _lock:
        attempts = _failures.get(client_key)
        if not attempts:
            return None
        while attempts and current - attempts[0] >= WINDOW_SECONDS:
            attempts.popleft()
        if not attempts:
            _failures.pop(client_key, None)
            return None
        if len(attempts) < MAX_FAILURES:
            return None
        return max(1, int(WINDOW_SECONDS - (current - attempts[0])))


def record_login_failure(client_key: str, now: float | None = None) -> None:
    current = monotonic() if now is None else now
    with _lock:
        attempts = _failures.get(client_key)
        if attempts is None:
            if len(_failures) >= MAX_TRACKED_CLIENTS:
                # Drop the oldest client bucket to keep memory bounded.
                oldest_key = min(_failures, key=lambda key: _failures[key][0] if _failures[key] else current)
                _failures.pop(oldest_key, None)
            attempts = deque()
            _failures[client_key] = attempts
        while attempts and current - attempts[0] >= WINDOW_SECONDS:
            attempts.popleft()
        attempts.append(current)


def clear_login_failures(client_key: str) -> None:
    with _lock:
        _failures.pop(client_key, None)


def reset_login_limits() -> None:
    """Clear buckets, primarily for isolated tests."""
    with _lock:
        _failures.clear()
