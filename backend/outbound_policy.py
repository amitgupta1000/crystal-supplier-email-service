import asyncio
import logging
import os
import random
import time
from collections import deque
from typing import Deque, Dict

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class OutboundPolicy:
    """In-process outbound throttle to reduce spam-like sending patterns."""

    def __init__(self) -> None:
        base_rate_limit = _env_int("RATE_LIMIT_REQUESTS", 100)
        base_window = _env_int("RATE_LIMIT_WINDOW", 60)

        self.max_per_window = _env_int("OUTBOUND_MAX_PER_WINDOW", base_rate_limit)
        self.window_seconds = _env_int("OUTBOUND_WINDOW_SECONDS", base_window)
        self.min_interval_seconds = _env_float("OUTBOUND_MIN_INTERVAL_SECONDS", 0.75)
        self.recipient_cooldown_seconds = _env_int("OUTBOUND_RECIPIENT_COOLDOWN_SECONDS", 300)
        self.jitter_ms = _env_int("OUTBOUND_JITTER_MS", 300)

        self._send_timestamps: Deque[float] = deque()
        self._recipient_last_sent: Dict[str, float] = {}
        self._last_global_sent_at = 0.0
        self._lock = asyncio.Lock()

    async def reserve_send_slot(self, to_email: str) -> tuple[float, float]:
        """Reserve next send slot.

        Returns:
            (waited_before_reserve_seconds, jitter_delay_seconds)
        """
        email_key = (to_email or "").strip().lower()
        start = time.monotonic()

        while True:
            async with self._lock:
                now = time.monotonic()
                cutoff = now - self.window_seconds

                while self._send_timestamps and self._send_timestamps[0] < cutoff:
                    self._send_timestamps.popleft()

                waits = []

                if self.max_per_window > 0 and len(self._send_timestamps) >= self.max_per_window:
                    waits.append((self._send_timestamps[0] + self.window_seconds) - now)

                if self.min_interval_seconds > 0 and self._last_global_sent_at > 0:
                    waits.append((self._last_global_sent_at + self.min_interval_seconds) - now)

                if email_key and self.recipient_cooldown_seconds > 0:
                    recipient_last = self._recipient_last_sent.get(email_key)
                    if recipient_last is not None:
                        waits.append((recipient_last + self.recipient_cooldown_seconds) - now)

                max_wait = max([w for w in waits if w > 0], default=0.0)
                if max_wait <= 0:
                    jitter_delay = random.uniform(0.0, max(self.jitter_ms, 0) / 1000.0)
                    scheduled = now + jitter_delay

                    self._send_timestamps.append(scheduled)
                    self._last_global_sent_at = scheduled
                    if email_key:
                        self._recipient_last_sent[email_key] = scheduled

                    if jitter_delay > 0:
                        logger.info("Outbound policy jitter %.2fs for %s", jitter_delay, to_email)
                    waited_before_reserve = max(0.0, time.monotonic() - start)
                    return waited_before_reserve, jitter_delay

            await asyncio.sleep(min(max_wait, 5.0))


_outbound_policy_singleton: OutboundPolicy | None = None


def get_outbound_policy() -> OutboundPolicy:
    global _outbound_policy_singleton
    if _outbound_policy_singleton is None:
        _outbound_policy_singleton = OutboundPolicy()
    return _outbound_policy_singleton
