# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/update_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The header inside a firmware image, read from an update that passes through the gateway.

The update identifiers are dangerous ones: they cross only when the operator unlocks them. When they do, this guard follows each update (the start frame with the
size and the hardware, then the data) and reads the first bytes of the image, where an image built with the header slot sealed carries its 32-byte header at the
fixed offset ``EMBED_OFFSET``. The header must hold (its CRC, the embedded form, no signature trailer), state the length the start frame announced and the hardware
the start frame named. Otherwise the rest of that update is refused, and stays refused until a new start frame: the board is still
waiting for it, so a second end frame (from this connection or from a later one) must not reach it. An image with no header follows the switch ``update_image.header``: ``accept`` forwards it,
``warn`` (the default) forwards it and leaves a note in the audit, ``require`` refuses it.

What it cannot do: the bytes before the decision (the first ``EMBED_OFFSET + 32``) have already crossed, so a refused update is cut, not prevented from starting. The
board never gets the end frame, it does not install anything, and its own verification of the image (CRC-32 and signature) is the check that decides what runs. The
CRC-32 of the whole image is the board's to check. A frame that is not part of an update is not looked at.

The board does not forget when the gateway restarts, so neither does a guard that is given a state file: the refused updates are written there and read back at start,
and so are the updates whose header has not been read yet. Those cannot be checked any more after a restart (the first bytes are gone), so they come back refused.
A file that is there but cannot be read counts as every kind of update refused (a new start frame clears it, as for any refusal).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import image_header as ih
from . import urtc_protocol as proto

# (start, data, end) of the two kinds of update that carry an image
KINDS = {
    "main": (proto.CAN_ID_START_UPDATE, proto.CAN_ID_DATA, proto.CAN_ID_END_UPDATE),
    "slave": (proto.CAN_ID_SLAVE_START_UPDATE, proto.CAN_ID_SLAVE_DATA, proto.CAN_ID_SLAVE_END_UPDATE),
}
NEEDED = ih.EMBED_OFFSET + ih.HEADER_SIZE
STATE_SCHEMA = 1
MAX_STATE_BYTES = 4096
UNREADABLE = "the record of refused updates could not be read"
CUT_BY_RESTART = "the gateway was restarted before the header of this update had been read"


def default_state_file(bus: str) -> Path:
    """Where the refused updates of the bus named ``bus`` (a port or a URL) are kept when no file is given: one file per bus, in the home folder."""
    name = os.path.normcase(bus)
    readable = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:40] or "bus"
    return Path.home() / ".urtc-gateway" / f"refused-updates-{readable}-{hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]}.json"


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
    def __init__(self, policy: str = ih.DEFAULT_POLICY, state_file: str | Path | None = None, log: Callable[[str], None] | None = None) -> None:
        """``state_file`` keeps the refused and the unchecked updates across restarts (none: they live as long as this object); ``log`` is told when it cannot be read or written."""
        self.policy = ih.parse_policy(policy)
        self.state_file = Path(state_file) if state_file else None
        self._log = log or (lambda text: None)
        self._updates: dict[str, _Update] = {}
        for kind, reason in self._load().items():
            self._updates[kind] = _Update(0, 0, decided=True, refused=reason)

    def refused_kinds(self) -> list[str]:
        """The kinds of update that are refused until a new start frame."""
        return sorted(kind for kind, update in self._updates.items() if update.refused)

    def _load(self) -> dict[str, str]:
        if self.state_file is None:
            return {}
        try:
            with self.state_file.open("rb") as handle:
                raw = handle.read(MAX_STATE_BYTES + 1)
            if len(raw) > MAX_STATE_BYTES:
                raise ValueError("too long")
            data = json.loads(raw.decode("utf-8-sig"))
            refused = data["refused"]
            if data["schema"] != STATE_SCHEMA or not isinstance(refused, dict):
                raise ValueError("not the expected form")
            if not all(kind in KINDS and isinstance(reason, str) and reason for kind, reason in refused.items()):
                raise ValueError("not the expected form")
            pending = data.get("pending", [])   # not in a file written by an earlier version
            if not isinstance(pending, list) or not all(isinstance(kind, str) and kind in KINDS for kind in pending):
                raise ValueError("not the expected form")
            return {**dict.fromkeys(pending, CUT_BY_RESTART), **refused}
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
            self._log(f"{UNREADABLE} ({self.state_file}: {error.__class__.__name__}); every update is refused until a new start frame")
            return dict.fromkeys(KINDS, UNREADABLE)

    def _save(self) -> None:
        if self.state_file is None:
            return
        refused = {kind: update.refused for kind, update in self._updates.items() if update.refused}
        pending = sorted(kind for kind, update in self._updates.items() if not update.decided and not update.refused)
        temporary = self.state_file.with_name(self.state_file.name + ".tmp")
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump({"schema": STATE_SCHEMA, "refused": refused, "pending": pending}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_file)
        except OSError as error:
            self._log(f"the record of refused updates could not be written ({self.state_file}: {error.__class__.__name__}); a restart would not remember them")

    def check(self, can_id: int, data: bytes) -> Verdict:
        for kind, (start, data_id, end) in KINDS.items():
            if can_id == start:
                if len(data) >= 8:
                    size, hardware = struct.unpack(">II", bytes(data[:8]))
                    self._updates[kind] = _Update(size, hardware)
                    self._save()
                elif kind in self._updates and not self._updates[kind].refused:
                    del self._updates[kind]
                    self._save()
                return PASS
            if can_id == data_id:
                return self._data(kind, data)
            if can_id == end:
                update = self._updates.get(kind)
                if update is not None and update.refused:
                    return Verdict(True, "bad_image_header", f"the {kind} update was refused earlier: {update.refused}")
                ended = self._updates.pop(kind, None)
                if ended is not None and not ended.decided:
                    self._save()
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
        verdict = self._look(kind, update)
        if update.decided:
            self._save()   # the header was judged: the update is no longer an unchecked one
        return verdict

    def _look(self, kind: str, update: _Update) -> Verdict:
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
