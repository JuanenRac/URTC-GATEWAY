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
* ``outbound``   frames the bus may send to the network: what a board sends (``board_to_host`` and ``both``) and the reply of the tool rack
                 (the frames of the ``rack`` section of the specification that go ``rack_to_host``, today ``0x261``).

An identifier that is in none of them (unknown, one the board only sends, or any frame of the rack) is not forwarded towards the bus: the rack order
``0x260`` and the rack reply ``0x261`` are refused towards the bus, and only the reply is forwarded towards the network.
"""
from __future__ import annotations

from typing import Any, cast

from . import urtc_protocol as proto

# the table of the shared protocol copy, typed as what it is (the copy is generated and is not edited here)
MESSAGES = cast("dict[int, dict[str, Any]]", proto.MESSAGES)
RACK_NAMES = cast("dict[int, str]", proto.RACK_NAMES)
RACK_DIRECTIONS = cast("dict[int, str]", proto.RACK_DIRECTIONS)

LOCKED_GROUPS = {"bootloader", "slave_bridge"}
PERSISTENT_NAMES = {"PID_CONFIG"}


def dangerous_reason(can_id: int) -> str | None:
    """Why an identifier is dangerous to forward, or None when it is not."""
    info = MESSAGES.get(can_id)
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
    return {i: m for i, m in MESSAGES.items() if m["direction"] in ("host_to_board", "both")}


def inbound_ids() -> frozenset[int]:
    return frozenset(i for i in _from_hosts() if dangerous_reason(i) is None)


def dangerous_ids() -> frozenset[int]:
    return frozenset(i for i in _from_hosts() if dangerous_reason(i) is not None)


def rack_ids() -> frozenset[int]:
    """The identifiers of the tool rack (the ``rack`` section of the specification, outside the messages of the tool head)."""
    return frozenset(RACK_DIRECTIONS)


def outbound_ids() -> frozenset[int]:
    from_boards = frozenset(i for i, m in MESSAGES.items() if m["direction"] in ("board_to_host", "both"))
    return from_boards | frozenset(i for i, direction in RACK_DIRECTIONS.items() if direction == "rack_to_host")


def name_of(can_id: int) -> str:
    info = MESSAGES.get(can_id)
    if info:
        return info["name"]
    return "RACK_" + RACK_NAMES[can_id] if can_id in RACK_NAMES else f"0x{can_id:03X}"


def table_markdown() -> str:
    """The table of docs/ALLOWED_IDS.md: every identifier of the specification and what the gateway does with it."""
    inbound, dangerous, outbound = inbound_ids(), dangerous_ids(), outbound_ids()
    lines = ["<!-- GENERATED from the protocol specification by tools/make_id_table.py - do not edit by hand. -->", "",
             "# Identifiers and the gateway", "",
             "| Identifier | Name | Towards the bus | Towards the network |", "|---|---|---|---|"]
    for can_id in sorted(set(MESSAGES) | rack_ids()):
        if can_id in inbound:
            to_bus = "forwarded"
        elif can_id in dangerous:
            to_bus = "refused (dangerous)"
        else:
            to_bus = "refused"
        lines.append(f"| 0x{can_id:03X} | {name_of(can_id)} | {to_bus} | {'forwarded' if can_id in outbound else 'refused'} |")
    return "\n".join(lines) + "\n"
