# =============================================================================
# URTC-GATEWAY - tests/test_peer_limits.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a peer may do before it proves its key, and for how long a stalled peer holds the gateway: the send timeout, the authentication deadline and the bus frames that
wait for the key."""
from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from urtc_gateway import urtc_protocol as proto
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, warnings
from urtc_gateway.gateway import Gateway, sign_message
from urtc_gateway.serve import LoopbackBus, _send_all, serve_connection

KEY = bytes(range(32))
ANSWER = proto.CAN_ID_ACTIVE_TOOL_RESP
SOLDER = proto.CAN_ID_SOLDER_SETPOINT


def make(config: GatewayConfig):
    net: list = []
    gateway = Gateway(config, {"controller": KEY}, lambda i, d: None, net.append, time.monotonic)
    return gateway, net


# ---- the options -------------------------------------------------------------------------------------------------------------------------
def test_the_defaults_are_the_conservative_ones():
    server = GatewayConfig().server
    assert server.send_timeout_s == 30.0 and server.auth_timeout_s == 30.0 and server.forward_bus_before_auth is False


def test_the_options_come_from_the_file_and_negative_times_are_refused():
    server = config_from_dict({"server": {"send_timeout_s": 5, "auth_timeout_s": 0, "forward_bus_before_auth": True}}).server
    assert (server.send_timeout_s, server.auth_timeout_s, server.forward_bus_before_auth) == (5, 0, True)
    with pytest.raises(ConfigError):
        config_from_dict({"server": {"send_timeout_s": -1}})
    with pytest.raises(ConfigError):
        config_from_dict({"server": {"auth_timeout_s": "soon"}})


def test_loosening_them_is_said_at_start():
    text = " ".join(warnings(config_from_dict({"server": {"send_timeout_s": 0, "auth_timeout_s": 0, "forward_bus_before_auth": True}})))
    assert "send timeout is OFF" in text and "authentication deadline is OFF" in text and "before it has proved its key" in text
    assert warnings(GatewayConfig()) == []
    assert not any("deadline" in w for w in warnings(config_from_dict({"session": {"enabled": False}, "server": {"auth_timeout_s": 0}})))


# ---- the bus waits for the key -----------------------------------------------------------------------------------------------------------
def test_a_frame_of_the_bus_is_not_shown_to_a_peer_that_has_not_proved_its_key():
    gateway, net = make(GatewayConfig())
    gateway.hello()
    decision = gateway.from_bus(ANSWER, bytes(4))
    assert not decision and decision.code == "unauthenticated" and net == []
    assert gateway.stats.refused["out_unauthenticated"] == 1
    assert gateway.from_network(sign_message(KEY, gateway.session.nonce, "controller", 1, SOLDER, b"\x01\x2C"))
    assert gateway.from_bus(ANSWER, bytes(4)) and len(net) == 1


def test_the_health_frames_are_still_kept_for_the_judgement_of_the_bus():
    gateway, _ = make(GatewayConfig())
    gateway.hello()
    gateway.from_bus(0x1B8, bytes(8))
    assert len(gateway.health_frames) == 1


def test_with_the_option_on_the_frames_flow_from_the_start():
    gateway, net = make(config_from_dict({"server": {"forward_bus_before_auth": True}}))
    gateway.hello()
    assert gateway.from_bus(ANSWER, bytes(4)) and len(net) == 1


def test_without_sessions_nothing_is_held_back():
    gateway, net = make(config_from_dict({"session": {"enabled": False}}))
    gateway.hello()
    assert gateway.from_bus(ANSWER, bytes(4)) and len(net) == 1


def test_a_new_hello_asks_for_the_key_again():
    gateway, _ = make(GatewayConfig())
    gateway.hello()
    gateway.from_network(sign_message(KEY, gateway.session.nonce, "controller", 1, SOLDER, b"\x01\x2C"))
    assert gateway.authenticated
    gateway.hello()
    assert not gateway.authenticated


# ---- the send timeout --------------------------------------------------------------------------------------------------------------------
class StalledConn:
    """A peer that never reads: every write waits for the socket timeout and then times out."""

    def send(self, _view) -> int:
        time.sleep(0.01)
        raise TimeoutError("timed out")


def test_a_write_to_a_stalled_peer_gives_up_after_the_limit():
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        _send_all(StalledConn(), b"x" * 10, 0.1)
    assert 0.09 <= time.monotonic() - started < 2.0


def test_a_write_in_pieces_arrives_whole():
    class Slow:
        def __init__(self) -> None:
            self.got = b""
            self.turn = 0

        def send(self, view) -> int:
            self.turn += 1
            if self.turn % 2:
                raise TimeoutError("timed out")
            piece = bytes(view[:3])
            self.got += piece
            return len(piece)

    conn = Slow()
    _send_all(conn, b"0123456789", 5.0)
    assert conn.got == b"0123456789"


# ---- the authentication deadline ---------------------------------------------------------------------------------------------------------
def test_a_peer_that_never_proves_its_key_is_disconnected():
    config = config_from_dict({"server": {"auth_timeout_s": 0.4}})
    gateway = Gateway(config, {"controller": KEY}, lambda i, d: None, lambda m: None, time.monotonic)
    left, right = socket.socketpair()
    messages: list[str] = []
    worker = threading.Thread(target=serve_connection, args=(left, gateway, LoopbackBus(), threading.Event(), messages.append), daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(10.0)
    assert not worker.is_alive()
    assert 0.35 <= time.monotonic() - started < 5.0
    assert any("did not prove its key" in m for m in messages)
    left.close()
    right.close()


def test_a_peer_that_proves_its_key_in_time_is_kept():
    config = config_from_dict({"server": {"auth_timeout_s": 0.6}})
    gateway = Gateway(config, {"controller": KEY}, lambda i, d: None, lambda m: None, time.monotonic)
    left, right = socket.socketpair()
    stop = threading.Event()
    worker = threading.Thread(target=serve_connection, args=(left, gateway, LoopbackBus(), stop), daemon=True)
    worker.start()
    reader = right.makefile("rb")
    nonce = bytes.fromhex(json.loads(reader.readline())["nonce"])
    right.sendall(json.dumps(sign_message(KEY, nonce, "controller", 1, SOLDER, b"\x01\x2C")).encode() + b"\n")
    time.sleep(1.0)
    assert worker.is_alive()
    stop.set()
    worker.join(5.0)
    left.close()
    right.close()
