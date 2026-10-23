# =============================================================================
# URTC-GATEWAY - tests/test_serial_bus.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The SLCAN bus of the gateway reached through a pyserial URL (``socket://``) instead of a serial port.

A small SLCAN server stands in for the adapter, so no adapter and no board are needed. When the URTC-COMMON
repository is checked out beside this one, the same bus is also tried against its virtual board.
"""
from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

import pytest

from urtc_gateway import urtc_protocol as proto
from urtc_gateway.serve import SerialSlcanBus

pytest.importorskip("serial")


class FakeAdapter:
    """Accepts one connection, answers every command line with a CR and records what it was sent; ``push`` sends a line."""

    def __init__(self) -> None:
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.received: list[str] = []
        self.client: socket.socket | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"socket://127.0.0.1:{self.server.getsockname()[1]}"

    def _serve(self) -> None:
        try:
            self.client, _ = self.server.accept()
        except OSError:
            return
        self._ready.set()
        buffer = b""
        try:
            while True:
                chunk = self.client.recv(256)
                if not chunk:
                    return
                buffer += chunk
                while b"\r" in buffer:
                    line, _, buffer = buffer.partition(b"\r")
                    self.received.append(line.decode("ascii"))
                    self.client.sendall(b"\r")
        except OSError:
            return

    def push(self, line: str) -> None:
        assert self._ready.wait(5)
        assert self.client is not None
        self.client.sendall(line.encode("ascii") + b"\r")

    def wait_for(self, count: int) -> None:
        for _ in range(100):
            if len(self.received) >= count:
                return
            threading.Event().wait(0.05)

    def close(self) -> None:
        for sock in (self.client, self.server):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass


def test_a_serial_url_opens_the_bus_and_frames_cross_both_ways():
    adapter = FakeAdapter()
    try:
        bus = SerialSlcanBus(adapter.url, 500000)
        try:
            bus.send(0x7F8, b"\x00")
            adapter.wait_for(4)
            assert adapter.received[:3] == ["C", "S6", "O"]
            assert "t7F81" + "00" in adapter.received
            adapter.push("t7F9800000000000000AA")
            frame = None
            for _ in range(20):
                frame = bus.recv(0.2)
                if frame is not None:
                    break
            assert frame == (0x7F9, bytes.fromhex("00000000000000AA"))
        finally:
            bus.close()
    finally:
        adapter.close()


def test_a_bit_rate_the_adapter_does_not_take_is_refused_before_anything_opens():
    with pytest.raises(ValueError):
        SerialSlcanBus("socket://127.0.0.1:1", 123456)


def test_a_url_nobody_listens_on_raises():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    url = f"socket://127.0.0.1:{probe.getsockname()[1]}"
    probe.close()  # the port is free again and nothing listens on it
    with pytest.raises(Exception):  # noqa: B017 - pyserial raises SerialException or an OSError, depending on the platform
        SerialSlcanBus(url, 500000)


def test_the_bus_reaches_the_virtual_board_of_the_shared_package():
    common = Path(__file__).resolve().parents[2] / "URTC-COMMON" / "src"
    if not (common / "urtc_common" / "virtual_board.py").exists():
        pytest.skip("URTC-COMMON is not checked out beside this repository")
    sys.path.insert(0, str(common))
    try:
        from urtc_common.virtual_board import VirtualBoard, VirtualBoardServer
    finally:
        sys.path.remove(str(common))
    with VirtualBoardServer(VirtualBoard(version=(0, 4), patch=2)) as server:
        bus = SerialSlcanBus(server.url, 500000)
        try:
            bus.send(proto.CAN_ID_QUERY_VERSION, b"\x00")
            frame = None
            for _ in range(20):
                frame = bus.recv(0.2)
                if frame is not None:
                    break
        finally:
            bus.close()
    assert frame is not None and frame[0] == proto.CAN_ID_VERSION_RESPONSE
