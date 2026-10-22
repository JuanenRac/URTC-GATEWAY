# =============================================================================
# URTC-GATEWAY - src/urtc_gateway/session.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Session keys: a peer proves it holds a key shared with the gateway, and cannot replay what it sent before.

When a peer connects the gateway gives it a fresh random nonce. Every frame the peer sends carries a counter and a
message authentication code: HMAC-SHA256 over the label, the nonce, the counter, the identifier and the data, shortened to
16 bytes. The counter has to grow with every frame of the connection, and the nonce is different for every connection, so a
recorded frame is useless later and on another connection. This authenticates the peer; it does not encrypt (the bus is not a
secret), and it does not stop a peer that holds the key and misbehaves, which is what the identifier list and the rate limit are for.

A key file has one key per line: ``<peer name> <64 hexadecimal digits>``; a line starting with ``#`` is a comment. The file should be
readable by its owner only; the gateway says so when it is not (on systems that have file modes). A key is never printed.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import stat
from dataclasses import dataclass, field
from pathlib import Path

LABEL = b"urtc-gw/1"
MAC_BYTES = 16
KEY_BYTES = 32
_NAME = re.compile(r"[A-Za-z0-9._-]{1,32}")


class KeyError_(ValueError):  # not KeyError: this one is about key material
    """The key file or a key is not usable."""


def new_nonce() -> bytes:
    return secrets.token_bytes(16)


def mac(key: bytes, nonce: bytes, counter: int, can_id: int, data: bytes) -> bytes:
    message = b"|".join([LABEL, nonce, str(counter).encode(), f"{can_id:03X}".encode(), data.hex().encode()])
    return hmac.new(key, message, hashlib.sha256).digest()[:MAC_BYTES]


def load_keys(path: str | Path) -> dict[str, bytes]:
    """Read a key file. Raises KeyError_ for a line that is not ``name key``, a name or key of the wrong shape, or a repeated name."""
    keys: dict[str, bytes] = {}
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise KeyError_(f"line {number}: expected '<peer name> <64 hexadecimal digits>'")
        name, hexkey = parts
        if not _NAME.fullmatch(name):
            raise KeyError_(f"line {number}: the peer name may use letters, digits, '.', '_' and '-' (32 at most)")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", hexkey):
            raise KeyError_(f"line {number}: the key must be exactly 64 hexadecimal digits")
        if name in keys:
            raise KeyError_(f"line {number}: the peer {name!r} appears twice")
        keys[name] = bytes.fromhex(hexkey)
    if not keys:
        raise KeyError_("the key file holds no key")
    return keys


def key_file_is_private(path: str | Path) -> bool:
    """False when other users can read the file (checked only where the system has file modes)."""
    if os.name == "nt":
        return True
    mode = Path(path).stat().st_mode
    return not (mode & (stat.S_IRWXG | stat.S_IRWXO))


def write_new_key_file(path: str | Path, peers: list[str]) -> None:
    """Make a key file with a new random key per peer, readable by the owner only. Refuses to overwrite a file."""
    path = Path(path)
    if path.exists():
        raise KeyError_(f"{path} exists: it is not overwritten")
    for name in peers:
        if not _NAME.fullmatch(name):
            raise KeyError_(f"peer name {name!r} is not valid")
    if len(set(peers)) != len(peers) or not peers:
        raise KeyError_("give one or more different peer names")
    text = "# URTC-GATEWAY session keys: keep this file private. One key per peer.\n" + "".join(f"{n} {secrets.token_hex(KEY_BYTES)}\n" for n in peers)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


@dataclass
class Session:
    """The state of one connection: the nonce given to the peer and the last counter accepted."""
    keys: dict[str, bytes]
    nonce: bytes = field(default_factory=new_nonce)
    peer: str | None = None
    last_counter: int = -1

    def verify(self, peer: str, counter: int, can_id: int, data: bytes, tag: bytes) -> str | None:
        """None when the frame is authentic and new; otherwise the reason (``unknown_peer``, ``bad_mac``, ``replay``, ``wrong_peer``)."""
        key = self.keys.get(peer)
        if key is None:
            return "unknown_peer"
        if self.peer is not None and peer != self.peer:
            return "wrong_peer"       # one connection, one peer: a second name on the same connection is not accepted
        if isinstance(counter, bool) or not isinstance(counter, int) or counter < 0:
            return "bad_mac"
        expected = mac(key, self.nonce, counter, can_id, data)
        if not hmac.compare_digest(expected, tag):
            return "bad_mac"
        if counter <= self.last_counter:
            return "replay"
        self.peer = peer
        self.last_counter = counter
        return None
