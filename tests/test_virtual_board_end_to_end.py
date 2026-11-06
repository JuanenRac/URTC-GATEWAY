# =============================================================================
# URTC-GATEWAY - tests/test_virtual_board_end_to_end.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The whole gateway, from a network peer to a virtual board and back, with no adapter and no board.

A peer connects over TCP, proves it holds a session key, and sends frames; the gateway filters them and writes the ones it lets through to an SLCAN bus; behind that bus
is the virtual board of the shared package (URTC-COMMON), which answers like the application of a tool head. The answers come back through the outbound filter to the
peer. Every refusal is also checked from the other side: what the gateway refused never reached the board, and the board still answers afterwards.

The shared package is found beside this repository (``URTC-COMMON/src``) or in the folder the variable ``URTC_COMMON_SRC`` names; without it the tests are skipped, and the
continuous integration of this repository checks it out.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Any, Iterator

import pytest

from urtc_gateway import urtc_protocol as proto
from urtc_gateway.config import config_from_dict
from urtc_gateway.gateway import sign_message
from urtc_gateway.serve import SerialSlcanBus, run

pytest.importorskip("serial")

KEY = bytes(range(32))
PEER = "panel"


def _common_source() -> Path | None:
    for candidate in (os.environ.get("URTC_COMMON_SRC", ""), str(Path(__file__).resolve().parents[2] / "URTC-COMMON" / "src")):
        if candidate and (Path(candidate) / "urtc_common" / "virtual_board.py").exists():
            return Path(candidate)
    return None


COMMON = _common_source()
pytestmark = pytest.mark.skipif(COMMON is None, reason="URTC-COMMON is not available (set URTC_COMMON_SRC or check it out beside this repository)")


class Peer:
    """A network peer: reads the lines the gateway sends and signs the frames it writes."""

    def __init__(self, port: int) -> None:
        self.conn = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.buffer = b""
        hello = self.read()
        assert hello["type"] == "hello" and hello["session"] is True
        self.nonce = bytes.fromhex(hello["nonce"])
        self.counter = 0

    def read(self) -> dict[str, Any]:
        while b"\n" not in self.buffer:
            chunk = self.conn.recv(4096)
            assert chunk, "the gateway closed the connection"
            self.buffer += chunk
        line, _, self.buffer = self.buffer.partition(b"\n")
        message = json.loads(line)
        assert isinstance(message, dict)
        return message

    def write(self, message: dict[str, Any]) -> None:
        self.conn.sendall(json.dumps(message).encode("utf-8") + b"\n")

    def send(self, can_id: int, data: bytes = b"", key: bytes = KEY, counter: int | None = None) -> None:
        if counter is None:
            self.counter += 1
            counter = self.counter
        self.write(sign_message(key, self.nonce, PEER, counter, can_id, data))

    def answer(self) -> dict[str, Any]:
        return self.read()

    def close(self) -> None:
        self.conn.close()


@pytest.fixture()
def gateway() -> Iterator[int]:
    assert COMMON is not None
    sys.path.insert(0, str(COMMON))
    try:
        from urtc_common.virtual_board import VirtualBoard, VirtualBoardServer
    finally:
        sys.path.remove(str(COMMON))
    stop = threading.Event()
    ready = threading.Event()
    bound: list[int] = []
    config = config_from_dict({"server": {"port": 0}})
    with VirtualBoardServer(VirtualBoard(version=(0, 4), patch=None)) as board:
        bus = SerialSlcanBus(board.url, 500000)
        thread = threading.Thread(target=run, args=(config, {PEER: KEY}, bus, stop, lambda text: None, ready, bound), daemon=True)
        thread.start()
        assert ready.wait(5)
        try:
            yield bound[0]
        finally:
            stop.set()
            thread.join(5)
            bus.close()


def test_a_signed_version_query_reaches_the_board_and_the_answer_comes_back(gateway):
    peer = Peer(gateway)
    try:
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00")
        answer = peer.answer()
    finally:
        peer.close()
    assert answer["type"] == "frame" and answer["id"] == proto.CAN_ID_VERSION_RESPONSE


def test_a_frame_with_a_wrong_key_is_refused_and_never_reaches_the_board(gateway):
    peer = Peer(gateway)
    try:
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00", key=bytes(32))
        assert peer.answer() == {"type": "refused", "code": "bad_mac"}
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00")           # the next, correctly signed query is still answered: the refused one did not disturb the board
        assert peer.answer()["id"] == proto.CAN_ID_VERSION_RESPONSE
    finally:
        peer.close()


def test_a_replayed_counter_is_refused(gateway):
    peer = Peer(gateway)
    try:
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00")
        assert peer.answer()["type"] == "frame"
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00", counter=1)
        refused = peer.answer()
        assert refused == {"type": "refused", "code": "replay"}
    finally:
        peer.close()


def test_the_order_to_enter_the_bootloader_is_refused_and_the_board_stays_in_its_application(gateway):
    peer = Peer(gateway)
    try:
        peer.send(proto.CAN_ID_ENTER_BOOTLOADER, bytes.fromhex("42 4F 4F 54".replace(" ", "")))
        assert peer.answer()["type"] == "refused"
        peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00")
        assert peer.answer()["id"] == proto.CAN_ID_VERSION_RESPONSE      # an application answers a version query with 0x7F9, a bootloader with another frame
    finally:
        peer.close()


def test_many_queries_in_a_row_are_all_answered_or_throttled_never_lost_silently(gateway):
    peer = Peer(gateway)
    try:
        for _ in range(20):
            peer.send(proto.CAN_ID_QUERY_VERSION, b"\x00")
        answers = [peer.answer() for _ in range(20)]
    finally:
        peer.close()
    assert all(a["type"] in ("frame", "refused") for a in answers)
    assert any(a["type"] == "frame" for a in answers)
