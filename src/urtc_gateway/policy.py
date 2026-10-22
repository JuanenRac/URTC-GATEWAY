# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/policy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The rules applied to a frame: is its identifier allowed, is its payload one the specification allows, is it too fast."""
from __future__ import annotations

from dataclasses import dataclass

from . import ids
from . import urtc_protocol as proto
from .config import GatewayConfig
from .ratelimit import RateLimiter, TokenBucket

LAYOUTS_BY_ID: dict[int, list[dict]] = {}
for _layout in proto.LAYOUTS.values():
    LAYOUTS_BY_ID.setdefault(_layout["id"], []).append(_layout)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str            # ok, not_listed, dangerous, bad_payload, rate_limited, ...
    detail: str = ""

    def __bool__(self) -> bool:
        return self.allowed


OK = Decision(True, "ok")


def _length_ok(rule: dict, n: int) -> bool:
    if rule.get("any"):
        return 0 <= n <= 8
    if "exact" in rule:
        return n == rule["exact"]
    if "one_of" in rule:
        return n in rule["one_of"]
    return rule["min"] <= n <= rule["max"]


def _field_problem(field: dict, data: bytes) -> str | None:
    offset = field.get("offset", 0)
    if field["type"] == "bytes":
        if "fixed" in field:
            width = field.get("length", len(bytes.fromhex(field["fixed"])))
            if data[offset:offset + width] != bytes.fromhex(field["fixed"]):
                return f"{field['name']} is not the required fixed bytes"
        return None
    width = field.get("width", 0)
    if offset + width > len(data):
        return None if field.get("optional") else f"{field['name']} is missing"
    value = int.from_bytes(data[offset:offset + width], "big", signed=field["type"].startswith("i"))
    if "range" in field and not field["range"][0] <= value <= field["range"][1]:
        return f"{field['name']} {value} is outside {field['range'][0]}..{field['range'][1]}"
    if "allowed" in field and value not in field["allowed"]:
        return f"{field['name']} {value} is not one of the defined values"
    return None


def payload_problem(can_id: int, data: bytes) -> str | None:
    """None when the frame is one the specification allows a host to send, else a sentence saying why not."""
    candidates = [lay for lay in LAYOUTS_BY_ID.get(can_id, []) if lay["role"] == "request"]
    if not candidates:
        return None   # nothing to compare with (an identifier that has only an answer layout is refused by the list, not here)
    best = "no request layout fits the length"
    for layout in candidates:
        if not _length_ok(layout["dlc"], len(data)):
            continue
        problems = [p for p in (_field_problem(f, data) for f in layout["fields"]) if p]
        if not problems:
            return None
        best = problems[0]
    return best


class Policy:
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        base = set(ids.inbound_ids())
        if config.whitelist.unlock_dangerous:
            base |= ids.dangerous_ids()
        base |= set(config.whitelist.extra_allow)
        base -= set(config.whitelist.deny)
        self.inbound = frozenset(base)
        self.dangerous = ids.dangerous_ids()
        self.outbound = ids.outbound_ids()
        r = config.rate
        overrides = {int(k, 16): (v[0], v[1]) for k, v in r.overrides.items()}
        for can_id in self.dangerous:
            overrides.setdefault(can_id, (r.dangerous_hz, r.dangerous_burst))
        self.limiter = RateLimiter(r.global_hz, r.global_burst, r.per_id_hz, r.per_id_burst, overrides) if r.enabled and r.global_hz > 0 and r.per_id_hz > 0 else None
        self.outbound_bucket = TokenBucket(config.outbound.rate_hz, max(1.0, config.outbound.rate_hz / 10)) if config.outbound.enabled and config.outbound.rate_hz > 0 else None

    def check_inbound(self, can_id: int, data: bytes, now_s: float) -> Decision:
        if not isinstance(can_id, int) or isinstance(can_id, bool) or not 0 <= can_id <= 0x7FF or len(data) > 8:
            return Decision(False, "bad_frame", "not a classic CAN frame")
        wl = self.config.whitelist
        if wl.enabled or can_id in wl.deny:
            if can_id in wl.deny:
                return Decision(False, "denied", f"0x{can_id:03X} is on the deny list")
            if can_id not in self.inbound:
                reason = ids.dangerous_reason(can_id)
                if reason and can_id in self.dangerous:
                    return Decision(False, "dangerous", f"0x{can_id:03X} {ids.name_of(can_id)} is refused: {reason}")
                return Decision(False, "not_listed", f"0x{can_id:03X} is not an identifier a host sends")
        if self.config.payload.enabled:
            problem = payload_problem(can_id, data)
            if problem:
                return Decision(False, "bad_payload", f"0x{can_id:03X}: {problem}")
        if self.limiter is not None and not self.limiter.allow(can_id, now_s):
            return Decision(False, "rate_limited", f"0x{can_id:03X} is sent too often")
        return OK

    def check_outbound(self, can_id: int, now_s: float) -> Decision:
        if self.config.outbound.enabled:
            if can_id not in self.outbound:
                return Decision(False, "not_listed", f"0x{can_id:03X} is not an identifier a board sends")
            if self.outbound_bucket is not None and not self.outbound_bucket.allow(now_s):
                return Decision(False, "rate_limited", "too many frames towards the network")
        return OK
