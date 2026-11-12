# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/update_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The header inside a firmware image, read from an update that passes through the gateway.

The update identifiers are dangerous ones: they cross only when the operator unlocks them. When they do, this guard follows each update (the start frame with the
size and the hardware, then the data) and reads the first bytes of the image, where an image built with the header slot sealed carries its 32-byte header at the
fixed offset ``EMBED_OFFSET``. The header must hold (its CRC, the embedded form, no signature trailer), state the length the start frame announced and the hardware
the start frame named. Otherwise the rest of that update is refused. An image with no header follows the switch ``update_image.header``: ``accept`` forwards it,
``warn`` (the default) forwards it and leaves a note in the audit, ``require`` refuses it.

What it cannot do: the bytes before the decision (the first ``EMBED_OFFSET + 32``) have already crossed, so a refused update is cut, not prevented from starting. The
board never gets the end frame, it does not install anything, and its own verification of the image (CRC-32 and signature) is the check that decides what runs. The
CRC-32 of the whole image is the board's to check. A frame that is not part of an update is not looked at.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import image_header as ih
from . import urtc_protocol as proto

# (start, data, end) of the two kinds of update that carry an image
KINDS = {
    "main": (proto.CAN_ID_START_UPDATE, proto.CAN_ID_DATA, proto.CAN_ID_END_UPDATE),
    "slave": (proto.CAN_ID_SLAVE_START_UPDATE, proto.CAN_ID_SLAVE_DATA, proto.CAN_ID_SLAVE_END_UPDATE),
}
NEEDED = ih.EMBED_OFFSET + ih.HEADER_SIZE


@dataclass
class Verdict:
    refused: bool
    code: str = "ok"      # ok, ok_no_header, bad_image_header
    detail: str = ""


PASS = Verdict(False)


@dataclass
class _Update:
    size: int
    hardware: int
    seen: bytearray = field(default_factory=bytearray)
    decided: bool = False
    refused: str = ""


class UpdateGuard:
    def __init__(self, policy: str = ih.DEFAULT_POLICY) -> None:
        self.policy = ih.parse_policy(policy)
        self._updates: dict[str, _Update] = {}

    def check(self, can_id: int, data: bytes) -> Verdict:
        for kind, (start, data_id, end) in KINDS.items():
            if can_id == start:
                if len(data) >= 8:
                    size, hardware = struct.unpack(">II", bytes(data[:8]))
                    self._updates[kind] = _Update(size, hardware)
                else:
                    self._updates.pop(kind, None)
                return PASS
            if can_id == data_id:
                return self._data(kind, data)
            if can_id == end:
                update = self._updates.pop(kind, None)
                if update is not None and update.refused:
                    return Verdict(True, "bad_image_header", f"the {kind} update was refused earlier: {update.refused}")
                return PASS
        return PASS

    def active(self, kind: str) -> bool:
        return kind in self._updates

    def _data(self, kind: str, data: bytes) -> Verdict:
        update = self._updates.get(kind)
        if update is None:
            return PASS   # no start frame was seen: nothing to compare with, the board refuses it by itself
        if update.refused:
            return Verdict(True, "bad_image_header", f"the {kind} update was refused: {update.refused}")
        if update.decided:
            return PASS
        update.seen += bytes(data)
        if len(update.seen) >= ih.EMBED_OFFSET + 4 and bytes(update.seen[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 4]) != struct.pack(">I", ih.MAGIC):
            return self._no_header(kind, update)
        if len(update.seen) >= update.size and len(update.seen) < NEEDED:
            return self._no_header(kind, update)   # an image too short to hold the slot
        if len(update.seen) < NEEDED:
            return PASS
        return self._header(kind, update)

    def _no_header(self, kind: str, update: _Update) -> Verdict:
        update.decided = True
        if self.policy == ih.POLICY_REQUIRE:
            update.refused = "the image has no header and the switch requires one"
            return Verdict(True, "bad_image_header", f"the {kind} update is refused: {update.refused}")
        if self.policy == ih.POLICY_WARN:
            return Verdict(False, "ok_no_header", f"the {kind} update carries an image with no header: its hardware and version were not checked")
        return PASS

    def _header(self, kind: str, update: _Update) -> Verdict:
        update.decided = True
        slot = bytes(update.seen[ih.EMBED_OFFSET:NEEDED])
        status, info = ih.parse_header(slot)
        problem = ""
        if status != ih.OK or info is None:
            problem = "the header inside the image is not valid (" + ih.STATUS_NAMES[status] + ")"
        elif not info.embedded or info.signed:
            problem = "the header is not the form that sits inside the image"
        elif info.payload_length != update.size:
            problem = f"the header states {info.payload_length} bytes but the update announced {update.size}"
        elif info.hardware_id != update.hardware:
            problem = f"the header is for hardware 0x{info.hardware_id:08X} but the update names 0x{update.hardware:08X}"
        if problem:
            update.refused = problem
            return Verdict(True, "bad_image_header", f"the {kind} update is refused: {problem}")
        return PASS
