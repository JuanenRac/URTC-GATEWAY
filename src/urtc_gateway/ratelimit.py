# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/ratelimit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Token buckets: a rate in frames per second with a burst, per identifier and for the whole link. Time is passed in."""
from __future__ import annotations


class TokenBucket:
    def __init__(self, rate_hz: float, burst: float) -> None:
        if rate_hz <= 0 or burst < 1:
            raise ValueError("a rate limit needs a positive rate and a burst of at least 1")
        self.rate_hz = float(rate_hz)
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last_s: float | None = None

    def allow(self, now_s: float) -> bool:
        if self.last_s is not None:
            elapsed = max(0.0, now_s - self.last_s)
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate_hz)
        self.last_s = now_s
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    """One bucket for everything and one for each identifier; a frame needs a token from both."""

    def __init__(self, global_hz: float, global_burst: float, per_id_hz: float, per_id_burst: float,
                 overrides: dict[int, tuple[float, float]] | None = None) -> None:
        self.global_bucket = TokenBucket(global_hz, global_burst)
        self.default = (per_id_hz, per_id_burst)
        self.overrides = dict(overrides or {})
        self.buckets: dict[int, TokenBucket] = {}

    def allow(self, can_id: int, now_s: float) -> bool:
        bucket = self.buckets.get(can_id)
        if bucket is None:
            rate, burst = self.overrides.get(can_id, self.default)
            bucket = self.buckets[can_id] = TokenBucket(rate, burst)
        # the identifier is asked first, so a flood of one identifier does not use up the tokens of the others
        if not bucket.allow(now_s):
            return False
        return self.global_bucket.allow(now_s)
