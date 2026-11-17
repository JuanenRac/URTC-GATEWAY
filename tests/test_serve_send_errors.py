# =============================================================================
# URTC-GATEWAY - tests/test_serve_send_errors.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A peer that cannot be written to ends its own connection and nothing more."""
from __future__ import annotations

import threading

from urtc_gateway import policy, serve
from urtc_gateway.serve import LoopbackBus


class BrokenConn:
    """A connection that sends some lines and then fails every send, like a peer that closed."""

    def __init__(self, lines: bytes, sends_before_failure: int) -> None:
        self._lines = lines
        self._sends = sends_before_failure

    def settimeout(self, _value) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        data, self._lines = self._lines, b""
        return data

    def sendall(self, _data: bytes) -> None:
        if self._sends <= 0:
            raise BrokenPipeError("peer gone")
        self._sends -= 1


class Gateway:
    to_network = None

    def hello(self):
        return {"type": "hello"}

    def from_bus(self, _can_id, _data):
        return None

    def from_network(self, _message):
        return policy.Decision(False, "bad_json", "not an object")


def test_a_failed_refusal_send_ends_only_that_connection():
    messages: list[str] = []
    conn = BrokenConn(b"{{{"+chr(10).encode()+b"{{{"+chr(10).encode(), sends_before_failure=1)     # the hello goes, the first refusal fails
    serve.serve_connection(conn, Gateway(), LoopbackBus(), threading.Event(), messages.append)
    assert any(m.startswith("peer lost") for m in messages)


def test_a_failed_hello_ends_only_that_connection():
    messages: list[str] = []
    conn = BrokenConn(b"", sends_before_failure=0)
    serve.serve_connection(conn, Gateway(), LoopbackBus(), threading.Event(), messages.append)
    assert any("before it was greeted" in m for m in messages)


def test_a_failed_accept_does_not_end_the_service(monkeypatch):
    """The listening loop logs a failed accept, counts it and keeps waiting for the next peer."""
    from urtc_gateway.config import GatewayConfig

    stop = threading.Event()
    messages: list[str] = []

    class FlakyServer:
        def __init__(self, *_args) -> None:
            self.calls = 0

        def setsockopt(self, *_args) -> None:
            pass

        def bind(self, _address) -> None:
            pass

        def listen(self, _backlog) -> None:
            pass

        def settimeout(self, _value) -> None:
            pass

        def getsockname(self):
            return ("127.0.0.1", 1)

        def accept(self):
            self.calls += 1
            if self.calls == 1:
                raise OSError("too many open files")
            stop.set()
            raise TimeoutError

        def close(self) -> None:
            pass

    monkeypatch.setattr(serve.socket, "socket", FlakyServer)
    timer = threading.Timer(10.0, stop.set)
    timer.start()
    try:
        serve.run(GatewayConfig(), None, LoopbackBus(), stop, messages.append)
    finally:
        timer.cancel()
    assert any(m.startswith("accept failed") and "1 connections dropped" in m for m in messages)
