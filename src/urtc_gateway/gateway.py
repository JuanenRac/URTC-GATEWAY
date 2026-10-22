# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/gateway.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The gateway itself: frames in from the network are authenticated and checked, frames from the bus are filtered on their way out.

No socket and no serial port here: the two ends are callables, and time is passed in, so the whole of it is tested without a bus.
"""
from __future__ import annotations

import collections
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import session as sessions
from .config import GatewayConfig
from .policy import Decision, Policy

MAX_AUDIT = 500


@dataclass
class Stats:
    forwarded_to_bus: int = 0
    forwarded_to_network: int = 0
    refused: collections.Counter = field(default_factory=collections.Counter)


class Gateway:
    """One gateway. ``to_bus(id, data)`` writes to the bus; ``to_network(message)`` sends a message to the peer."""

    def __init__(self, config: GatewayConfig, keys: dict[str, bytes] | None, to_bus: Callable[[int, bytes], None],
                 to_network: Callable[[dict[str, Any]], None], clock: Callable[[], float]) -> None:
        self.config = config
        self.policy = Policy(config)
        self.keys = keys or {}
        if config.session.enabled and not self.keys:
            raise sessions.KeyError_("session authentication is on but there is no key: give a key file or switch it off")
        self.to_bus = to_bus
        self.to_network = to_network
        self.clock = clock
        self.stats = Stats()
        self.audit: collections.deque[str] = collections.deque(maxlen=MAX_AUDIT)
        self.session = sessions.Session(self.keys)

    def hello(self) -> dict[str, Any]:
        """The first message to a peer that connects: the nonce its frames must be authenticated with."""
        self.session = sessions.Session(self.keys)
        return {"type": "hello", "gateway": "urtc-gateway/1", "session": self.config.session.enabled, "nonce": self.session.nonce.hex()}

    def _refuse(self, decision: Decision, who: str = "") -> Decision:
        self.stats.refused[decision.code] += 1
        self.audit.append(f"refused {decision.code}{' ' + who if who else ''}: {decision.detail}")
        return decision

    def from_network(self, message: Any) -> Decision:
        """Handle one message from the peer: {"id", "data", and, with sessions, "peer", "counter", "mac"}. Returns what was decided."""
        if not isinstance(message, dict):
            return self._refuse(Decision(False, "bad_frame", "a message is a JSON object"))
        try:
            can_id = message["id"]
            data = bytes.fromhex(message.get("data", ""))
        except (KeyError, ValueError, TypeError):
            return self._refuse(Decision(False, "bad_frame", "a message needs an id and the data as hexadecimal text"))
        if isinstance(can_id, bool) or not isinstance(can_id, int):
            return self._refuse(Decision(False, "bad_frame", "the id must be a number"))
        who = ""
        if self.config.session.enabled:
            peer, counter, tag = message.get("peer"), message.get("counter"), message.get("mac")
            if not isinstance(peer, str) or not isinstance(tag, str):
                return self._refuse(Decision(False, "auth_missing", "the message carries no peer name or MAC"))
            try:
                tag_bytes = bytes.fromhex(tag)
            except ValueError:
                return self._refuse(Decision(False, "bad_mac", "the MAC is not hexadecimal"), peer)
            problem = self.session.verify(peer, counter, can_id, data, tag_bytes)
            if problem:
                return self._refuse(Decision(False, problem, f"{problem.replace('_', ' ')}"), peer if isinstance(peer, str) else "")
            who = peer
        decision = self.policy.check_inbound(can_id, data, self.clock())
        if not decision:
            return self._refuse(decision, who)
        self.to_bus(can_id, data)
        self.stats.forwarded_to_bus += 1
        return decision

    def from_bus(self, can_id: int, data: bytes) -> Decision:
        """Handle one frame read from the bus: filter it and send it to the peer."""
        decision = self.policy.check_outbound(can_id, self.clock())
        if not decision:
            self.stats.refused["out_" + decision.code] += 1
            return decision
        self.to_network({"type": "frame", "id": can_id, "data": data.hex()})
        self.stats.forwarded_to_network += 1
        return decision

    def summary(self) -> dict[str, Any]:
        return {"to_bus": self.stats.forwarded_to_bus, "to_network": self.stats.forwarded_to_network, "refused": dict(self.stats.refused)}


def sign_message(key: bytes, nonce: bytes, peer: str, counter: int, can_id: int, data: bytes) -> dict[str, Any]:
    """What a peer sends: the frame with its counter and MAC (used by the tests and by anything that talks to the gateway)."""
    return {"id": can_id, "data": data.hex(), "peer": peer, "counter": counter, "mac": sessions.mac(key, nonce, counter, can_id, data).hex()}
