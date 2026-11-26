# =============================================================================
# URTC-GATEWAY - tests/test_cuts_and_bad_values.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Cut and damaged input: a serial line cut in the middle, noise on the port, an adapter that goes away, option values that
cannot work, files written by an editor with a byte-order mark and a peer that sends a very deeply nested message."""
from __future__ import annotations

import json
import socket
import sys
import threading
import types

import pytest

from urtc_gateway import cli, config, serve, session
from urtc_gateway.config import ConfigError, config_from_dict, load_config
from urtc_gateway.gateway import Gateway
from urtc_gateway.serve import LoopbackBus, SerialSlcanBus

KEY = "ab" * 32


class ScriptedPort:
    """A serial port that hands out what it was given, at most ``size`` bytes per read."""

    def __init__(self, *args, **kwargs):
        self.to_read = b""
        self.reads = 0

    @property
    def in_waiting(self):
        return len(self.to_read)

    def write(self, data):
        pass

    def read(self, size):
        self.reads += 1
        out, self.to_read = self.to_read[:size], self.to_read[size:]
        return out

    def close(self):
        pass


@pytest.fixture
def serial_bus(monkeypatch):
    module = types.ModuleType("serial")
    module.Serial = ScriptedPort
    module.serial_for_url = ScriptedPort
    monkeypatch.setitem(sys.modules, "serial", module)
    return SerialSlcanBus("COM9")


@pytest.mark.parametrize("line", [
    b"t1608010203\r",                # says 8 bytes and carries 3: cut on the way
    b"t160901020304050607 0809\r",   # a length no classic frame has
    b"t1609010203040506070809\r",
    b"t16020A\r",                    # one byte short
    b"t160101FF\r",                  # more bytes than it says
    b"tFFF100\r",                    # not a standard identifier
    b"t-12100\r",                    # a sign is not a digit
    b"t 12100\r",
    b"t160201 2\r",
    b"t160\r",
    b"z\r\a\r",
])
def test_a_damaged_serial_line_is_not_taken_for_a_frame(serial_bus, line):
    serial_bus._port.to_read = line + b"t16110A\r"
    assert serial_bus.recv(0.5) == (0x161, b"\x0a")


def test_an_adapter_time_stamp_after_the_data_is_accepted(serial_bus):
    serial_bus._port.to_read = b"t16110A1F3C\r"
    assert serial_bus.recv(0.5) == (0x161, b"\x0a")


def test_lines_already_received_are_handed_out_without_waiting_for_the_port(serial_bus):
    serial_bus._port.to_read = b"".join(b"t16110%X\r" % n for n in range(8))
    assert [serial_bus.recv(0.5)[1][0] for _ in range(8)] == list(range(8))
    assert serial_bus._port.reads <= 2 and serial_bus._buffer == b""


def test_a_flood_of_frames_does_not_build_up_a_backlog(serial_bus):
    serial_bus._port.to_read = b"t16080102030405060708\r" * 500
    for _ in range(500):
        assert serial_bus.recv(0.5) == (0x160, bytes(range(1, 9)))
        assert len(serial_bus._buffer) < 600


def test_noise_without_a_line_end_does_not_grow_the_buffer(serial_bus):
    serial_bus._port.to_read = b"\x55" * 100_000
    assert serial_bus.recv(0.1) is None
    assert len(serial_bus._buffer) <= 1100
    serial_bus._port.to_read = b"\rt16110A\r"
    assert serial_bus.recv(0.5) == (0x161, b"\x0a")


class UnpluggedBus(LoopbackBus):
    def recv(self, timeout):
        raise OSError("device disconnected")


def open_gateway():
    cfg = config_from_dict({"session": {"enabled": False}})
    return Gateway(cfg, None, lambda i, d: None, lambda m: None, lambda: 0.0)


def test_an_adapter_that_goes_away_ends_the_connection_and_says_so():
    mine, theirs = socket.socketpair()
    log: list[str] = []
    stop = threading.Event()
    worker = threading.Thread(target=serve.serve_connection, args=(theirs, open_gateway(), UnpluggedBus(), stop, log.append), daemon=True)
    worker.start()
    try:
        worker.join(timeout=5.0)
        assert not worker.is_alive(), "the connection went on without a bus"
        assert any("bus" in text for text in log), log
    finally:
        stop.set()
        mine.close()
        theirs.close()


def test_a_very_deeply_nested_message_is_refused_and_the_connection_goes_on(monkeypatch):
    real_loads = json.loads

    def loads(text, *args, **kwargs):
        if text.startswith("[["):
            raise RecursionError("maximum recursion depth exceeded")   # what Python 3.10 and 3.11 do with such a line
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr(serve.json, "loads", loads)
    mine, theirs = socket.socketpair()
    stop = threading.Event()
    gateway = open_gateway()
    worker = threading.Thread(target=serve.serve_connection, args=(theirs, gateway, LoopbackBus(), stop), daemon=True)
    worker.start()
    try:
        mine.settimeout(5.0)
        reader = mine.makefile("rb")
        reader.readline()
        mine.sendall(b"[" * 4000 + b"\n")
        assert real_loads(reader.readline())["code"] == "bad_frame"
    finally:
        stop.set()
        mine.close()
        worker.join(timeout=5.0)
        theirs.close()


@pytest.mark.parametrize("data", [
    {"rate": {"per_id_burst": 0}},
    {"rate": {"global_burst": 0.5}},
    {"rate": {"dangerous_burst": 0}},
    {"rate": {"dangerous_hz": 0}},
    {"rate": {"per_id_hz": float("nan")}},
    {"rate": {"global_burst": float("inf")}},
    {"outbound": {"rate_hz": float("nan")}},
    {"server": {"port": 8765.5}},
    {"server": {"idle_timeout_s": float("nan")}},
    {"rate": {"overrides": {"0x160": [5, 0.5]}}},
    {"rate": {"overrides": {"0x160": [float("nan"), 2]}}},
])
def test_a_value_the_gateway_cannot_run_with_is_refused_when_the_file_is_read(data):
    with pytest.raises(ConfigError):
        config_from_dict(data)


def test_a_rate_of_zero_that_switches_the_limit_off_is_named_in_the_warnings():
    for data in ({"rate": {"per_id_hz": 0}}, {"rate": {"global_hz": 0}}):
        text = " ".join(config.warnings(config_from_dict({**data, "session": {"enabled": False}})))
        assert "rate limit is OFF" in text, data
    assert "rate limit is OFF" not in " ".join(config.warnings(config_from_dict({})))


def test_files_saved_with_a_byte_order_mark_are_read(tmp_path):
    cfg = tmp_path / "gateway.json"
    cfg.write_bytes(b'\xef\xbb\xbf{"server": {"port": 9000}}')
    assert load_config(cfg).server.port == 9000
    keys = tmp_path / "keys.txt"
    keys.write_bytes(b"\xef\xbb\xbf# comment\r\nrobot " + KEY.encode() + b"\r\n")
    assert session.load_keys(keys) == {"robot": bytes.fromhex(KEY)}


def test_a_key_file_that_is_not_text_is_a_clear_error(tmp_path, capsys):
    keys = tmp_path / "keys.txt"
    keys.write_text(f"robot {KEY}\n", encoding="utf-16")   # what the redirection of an old PowerShell writes
    with pytest.raises(session.KeyError_, match="UTF-8"):
        session.load_keys(keys)
    assert cli.main(["run", "--key-file", str(keys)]) == 2
    assert KEY not in capsys.readouterr().err


def test_a_port_out_of_range_on_the_command_line_is_refused(capsys):
    for port in ("70000", "-1", "x"):
        with pytest.raises(SystemExit) as stop:
            cli.main(["run", "--no-session", "--port", port])
        assert stop.value.code == 2


def test_a_port_that_is_taken_is_a_message_and_not_a_traceback(capsys):
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen(1)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        taken.close()
        taken = socket.socket()
        taken.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)   # Windows lets SO_REUSEADDR take a port in use otherwise
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
    try:
        assert cli.main(["run", "--no-session", "--port", str(taken.getsockname()[1])]) == 2
        assert "cannot listen" in capsys.readouterr().err
    finally:
        taken.close()
