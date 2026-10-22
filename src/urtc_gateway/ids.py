# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/ids.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Which identifiers may cross the gateway, taken from the protocol specification (the copy in urtc_protocol.py).

Three sets are made from the specification, never typed by hand:

* ``inbound``    frames a peer on the network may send to the bus: the identifiers a host sends (``host_to_board`` and ``both``)
                 that are not dangerous;
* ``dangerous``  identifiers a host can send that change what the board is: the bootloader and the update of the expansion slave,
                 the erase of the saved state, every persistent setting. They are refused unless the operator unlocks them;
* ``outbound``   frames the bus may send to the network: what a board sends (``board_to_host`` and ``both``).

An identifier that is in none of them (unknown, or one the board only sends) is not forwarded towards the bus.
"""
from __future__ import annotations

from . import urtc_protocol as proto

LOCKED_GROUPS = {"bootloader", "slave_bridge"}
PERSISTENT_NAMES = {"PID_CONFIG"}


def dangerous_reason(can_id: int) -> str | None:
    """Why an identifier is dangerous to forward, or None when it is not."""
    info = proto.MESSAGES.get(can_id)
    if info is None:
        return None
    if info.get("gates", {}).get("needs_magic"):
        return "it needs a magic payload: it erases, resets or rewrites something that stays"
    if info["name"].startswith("QUERY_"):
        return None   # a question changes nothing, whatever group it is in (the version query, the error counters)
    if info["group"] in LOCKED_GROUPS:
        return "it belongs to the bootloader or to the update of the expansion slave"
    if info["name"].startswith("SET_") or info["name"] in PERSISTENT_NAMES:
        return "it changes a setting that is kept after a restart"
    return None


def _from_hosts() -> dict[int, dict]:
    return {i: m for i, m in proto.MESSAGES.items() if m["direction"] in ("host_to_board", "both")}


def inbound_ids() -> frozenset[int]:
    return frozenset(i for i in _from_hosts() if dangerous_reason(i) is None)


def dangerous_ids() -> frozenset[int]:
    return frozenset(i for i in _from_hosts() if dangerous_reason(i) is not None)


def outbound_ids() -> frozenset[int]:
    return frozenset(i for i, m in proto.MESSAGES.items() if m["direction"] in ("board_to_host", "both"))


def name_of(can_id: int) -> str:
    info = proto.MESSAGES.get(can_id)
    return info["name"] if info else f"0x{can_id:03X}"


def table_markdown() -> str:
    """The table of docs/ALLOWED_IDS.md: every identifier of the specification and what the gateway does with it."""
    inbound, dangerous, outbound = inbound_ids(), dangerous_ids(), outbound_ids()
    lines = ["<!-- GENERATED from the protocol specification by tools/make_id_table.py - do not edit by hand. -->", "",
             "# Identifiers and the gateway", "",
             "| Identifier | Name | Towards the bus | Towards the network |", "|---|---|---|---|"]
    for can_id in sorted(proto.MESSAGES):
        if can_id in inbound:
            to_bus = "forwarded"
        elif can_id in dangerous:
            to_bus = "refused (dangerous)"
        else:
            to_bus = "refused"
        lines.append(f"| 0x{can_id:03X} | {name_of(can_id)} | {to_bus} | {'forwarded' if can_id in outbound else 'refused'} |")
    return "\n".join(lines) + "\n"
