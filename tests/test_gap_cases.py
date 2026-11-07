# =============================================================================
# URTC-GATEWAY - tests/test_gap_cases.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Limits, failures and cuts the other tests do not reach: the options file, the length and fixed-byte rules, the serial end with a fake port
and the connection loop when the bus or the peer fails. Fast and deterministic: no adapter, no board, no network beyond a local socket pair."""
from __future__ import annotations

import io
import json
import random
import runpy
import socket
import sys
import threading
import types
import warnings

import pytest

from urtc_gateway import cli, config, policy, serve, session
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict, load_config
from urtc_gateway.serve import LoopbackBus, SerialSlcanBus


# ---- the options file -------------------------------------------------------------------------------------------------------------------
def test_a_configuration_that_is_not_an_object_is_refused():
    for bad in ([], "text", 3, None, True):
        with pytest.raises(ConfigError):
            config_from_dict(bad)


def test_unknown_sections_options_and_a_wrong_schema_are_refused():
    for bad in ({"nothing": {}}, {"schema": 2}, {"rate": {"nothing": 1}}, {"rate": 3}, {"whitelist": []}):
        with pytest.raises(ConfigError):
            config_from_dict(bad)


def test_the_type_of_each_option_is_checked():
    for bad in (
        {"whitelist": {"enabled": "yes"}},
        {"rate": {"per_id_hz": "fast"}},
        {"rate": {"per_id_hz": True}},
        {"rate": {"global_burst": -1}},
        {"server": {"port": 70000}},
        {"server": {"port": -1}},
        {"server": {"host": 5}},
        {"session": {"key_file": 5}},
        {"whitelist": {"extra_allow": "0x160"}},
        {"whitelist": {"deny": [1, "zz"]}},
        {"whitelist": {"deny": [0x800]}},
        {"whitelist": {"deny": [True]}},
        {"whitelist": {"deny": [-1]}},
    ):
        with pytest.raises(ConfigError):
            config_from_dict(bad)


def test_the_limits_of_the_port_and_of_the_identifiers_are_accepted():
    cfg = config_from_dict({"server": {"port": 0}, "whitelist": {"extra_allow": [0, "0x7FF", 0x160], "deny": ["0x100"]}})
    assert cfg.server.port == 0
    assert cfg.whitelist.extra_allow == [0, 0x7FF, 0x160]
    assert cfg.whitelist.deny == [0x100]
    assert config_from_dict({"server": {"port": 65535}}).server.port == 65535


def test_rate_overrides_are_checked_and_normalised():
    cfg = config_from_dict({"rate": {"overrides": {"0x160": [5, 2], 0x1C0: [1.5, 1]}}})
    assert cfg.rate.overrides == {"0x160": [5.0, 2.0], "0x1C0": [1.5, 1.0]}
    for bad in (
        {"overrides": []},
        {"overrides": {"0x160": 5}},
        {"overrides": {"0x160": [5]}},
        {"overrides": {"0x160": [5, 2, 1]}},
        {"overrides": {"0x160": [0, 2]}},
        {"overrides": {"0x160": [5, -2]}},
        {"overrides": {"0x160": [True, 2]}},
        {"overrides": {"0x160": ["5", 2]}},
        {"overrides": {"0x900": [5, 2]}},
        {"overrides": {"zz": [5, 2]}},
    ):
        with pytest.raises(ConfigError):
            config_from_dict({"rate": bad})


def test_the_configuration_round_trips_and_defaults_are_the_protected_ones(tmp_path):
    cfg = GatewayConfig()
    again = config_from_dict(config_to_dict(cfg))
    assert config_to_dict(again) == config_to_dict(cfg)
    assert cfg.whitelist.enabled and cfg.payload.enabled and cfg.rate.enabled and cfg.session.enabled and cfg.outbound.enabled
    assert not cfg.whitelist.unlock_dangerous and not cfg.server.allow_open_network
    assert config.warnings(cfg) == []
    path = tmp_path / "gateway.json"
    path.write_text(json.dumps(config_to_dict(cfg)), encoding="utf-8")
    assert config_to_dict(load_config(path)) == config_to_dict(cfg)


def test_a_missing_or_broken_file_is_a_clear_error(tmp_path):
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(bad)
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(empty)
    notobject = tmp_path / "list.json"
    notobject.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(notobject)


def test_every_loosened_protection_is_named_in_the_warnings():
    cfg = config_from_dict({"session": {"enabled": False}, "whitelist": {"enabled": False}})
    text = " ".join(config.warnings(cfg))
    assert "authentication is OFF" in text and "identifier list is OFF" in text
    cfg = config_from_dict({"whitelist": {"unlock_dangerous": True, "extra_allow": [0x160]}})
    text = " ".join(config.warnings(cfg))
    assert "UNLOCKED" in text and "0x160" in text
    only_one = config.warnings(config_from_dict({"session": {"enabled": False}}))
    assert len(only_one) == 1


def test_random_valid_options_always_load_and_round_trip():
    rng = random.Random(20260507)
    for _ in range(200):
        data = {
            "whitelist": {"enabled": rng.random() < 0.5, "unlock_dangerous": rng.random() < 0.5, "extra_allow": [rng.randrange(0x800) for _ in range(rng.randrange(4))]},
            "rate": {"per_id_hz": rng.uniform(0, 100), "global_burst": float(rng.randrange(0, 500)), "overrides": {f"0x{rng.randrange(0x800):03X}": [rng.uniform(0.1, 9), rng.uniform(0.1, 9)]}},
            "server": {"port": rng.randrange(0, 65536)},
        }
        cfg = config_from_dict(data)
        assert config_to_dict(config_from_dict(config_to_dict(cfg))) == config_to_dict(cfg)


# ---- the length and fixed-byte rules ---------------------------------------------------------------------------------------------------
def test_the_length_rules():
    assert policy._length_ok({"any": True}, 0) and policy._length_ok({"any": True}, 8)
    assert not policy._length_ok({"any": True}, 9)
    assert policy._length_ok({"exact": 3}, 3) and not policy._length_ok({"exact": 3}, 2)
    assert policy._length_ok({"one_of": [2, 4]}, 4) and policy._length_ok({"one_of": [2, 4]}, 2)
    assert not policy._length_ok({"one_of": [2, 4]}, 3) and not policy._length_ok({"one_of": [2, 4]}, 0)
    assert policy._length_ok({"min": 1, "max": 3}, 1) and policy._length_ok({"min": 1, "max": 3}, 3)
    assert not policy._length_ok({"min": 1, "max": 3}, 0) and not policy._length_ok({"min": 1, "max": 3}, 4)


def test_a_fixed_bytes_field_must_match_exactly():
    field = {"type": "bytes", "name": "magic", "fixed": "B0071D5A", "offset": 1}
    assert policy._field_problem(field, b"\x02\xb0\x07\x1d\x5a") is None
    assert "magic" in (policy._field_problem(field, b"\x02\xb0\x07\x1d\x5b") or "")
    assert policy._field_problem(field, b"\x02\xb0\x07") is not None          # cut short
    assert policy._field_problem(field, b"") is not None
    assert policy._field_problem({"type": "bytes", "name": "free"}, b"\x01") is None


# ---- the session key file ----------------------------------------------------------------------------------------------------------------
def test_a_peer_name_and_a_key_of_the_wrong_shape_are_refused(tmp_path):
    key = "ab" * 32
    cases = {
        "bad/name " + key: "peer name",
        "name " + key[:-1]: "64 hexadecimal",
        "name " + key + "00": "64 hexadecimal",
        "name " + "zz" * 32: "64 hexadecimal",
        "only-a-name": "expected",
        "a b c": "expected",
        ("n" * 33) + " " + key: "peer name",
    }
    for line, wanted in cases.items():
        path = tmp_path / "keys.txt"
        path.write_text(line + "\n", encoding="utf-8")
        with pytest.raises(session.KeyError_, match=wanted):
            session.load_keys(path)
    path.write_text("# only a comment\n\n", encoding="utf-8")
    with pytest.raises(session.KeyError_, match="no key"):
        session.load_keys(path)
    path.write_text(f"a {key}\na {key}\n", encoding="utf-8")
    with pytest.raises(session.KeyError_, match="twice"):
        session.load_keys(path)
    path.write_text(f"{'n' * 32} {key.upper()}\n", encoding="utf-8")
    assert session.load_keys(path) == {"n" * 32: bytes.fromhex(key)}


def test_the_mac_depends_on_every_field():
    key = b"k" * 32
    nonce = b"n" * 16
    base = session.mac(key, nonce, 1, 0x160, b"\x01")
    assert len(base) == session.MAC_BYTES
    assert session.mac(key, nonce, 1, 0x160, b"\x01") == base
    assert session.mac(b"j" * 32, nonce, 1, 0x160, b"\x01") != base
    assert session.mac(key, b"m" * 16, 1, 0x160, b"\x01") != base
    assert session.mac(key, nonce, 2, 0x160, b"\x01") != base
    assert session.mac(key, nonce, 1, 0x161, b"\x01") != base
    assert session.mac(key, nonce, 1, 0x160, b"\x02") != base
    assert session.new_nonce() != session.new_nonce()


# ---- the serial end, with a fake port ----------------------------------------------------------------------------------------------------
class FakePort:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.written: list[bytes] = []
        self.to_read = b""
        self.closed = False

    def write(self, data):
        self.written.append(bytes(data))

    def read(self, size):
        out, self.to_read = self.to_read[:size], self.to_read[size:]
        return out

    def close(self):
        self.closed = True


@pytest.fixture
def fake_serial(monkeypatch):
    module = types.ModuleType("serial")
    module.Serial = FakePort
    module.serial_for_url = FakePort
    monkeypatch.setitem(sys.modules, "serial", module)
    return module


def test_without_pyserial_the_serial_bus_says_so(monkeypatch):
    monkeypatch.setitem(sys.modules, "serial", None)
    with pytest.raises(RuntimeError, match="pyserial"):
        SerialSlcanBus("COM9")


def test_a_bit_rate_the_adapter_does_not_take_is_refused(fake_serial):
    for rate in (0, 1, 499999, 500001, 2000000):
        with pytest.raises(ValueError, match="bit rate"):
            SerialSlcanBus("COM9", bitrate=rate)


def test_every_bit_rate_code_opens_the_channel_in_order(fake_serial):
    for rate, code in SerialSlcanBus.BITRATE_CODES.items():
        bus = SerialSlcanBus("/dev/ttyUSB0", bitrate=rate)
        assert bus._port.written == [b"C\r", code.encode() + b"\r", b"O\r"]


def test_a_port_name_with_a_url_scheme_is_opened_as_a_url(fake_serial):
    bus = SerialSlcanBus("socket://127.0.0.1:7777")
    assert bus._port.args[0] == "socket://127.0.0.1:7777" and bus._port.kwargs["timeout"] == 0.05


def test_send_writes_a_standard_frame_and_close_closes_the_channel(fake_serial):
    bus = SerialSlcanBus("COM9")
    bus.send(0x160, b"\x01\x02")
    bus.send(0x7FF, b"")
    assert bus._port.written[-2:] == [b"t16020102\r", b"t7FF0\r"]
    bus.close()
    assert bus._port.written[-1] == b"C\r" and bus._port.closed


def test_close_closes_the_port_even_when_the_write_fails(fake_serial):
    bus = SerialSlcanBus("COM9")

    def broken(_data):
        raise OSError("unplugged")

    bus._port.write = broken
    with pytest.raises(OSError):
        bus.close()
    assert bus._port.closed


def test_recv_reads_frames_and_skips_what_is_not_a_frame(fake_serial):
    bus = SerialSlcanBus("COM9")
    bus._port.to_read = b"\rtxyz5\rt12\rT1234\rt1232AABB\rt0000\r"
    assert bus.recv(0.5) == (0x123, b"\xaa\xbb")
    assert bus.recv(0.5) == (0x000, b"")
    assert bus.recv(0.05) is None


def test_a_frame_that_arrives_in_pieces_is_put_together(fake_serial):
    bus = SerialSlcanBus("COM9")
    pieces = [b"t160", b"3010203", b"\r"]
    bus._port.read = lambda _n: pieces.pop(0) if pieces else b""
    assert bus.recv(1.0) == (0x160, b"\x01\x02\x03")


def test_the_loopback_bus_keeps_what_is_sent_and_returns_what_is_injected():
    bus = LoopbackBus()
    bus.send(0x160, bytearray(b"\x01"))
    assert bus.sent == [(0x160, b"\x01")]
    assert bus.recv(0.01) is None
    bus.inject(0x111, b"\x09")
    assert bus.recv(0.5) == (0x111, b"\x09")
    assert bus.close() is None


# ---- the connection loop ------------------------------------------------------------------------------------------------------------------
class OneChunkThenFail:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def settimeout(self, _t):
        pass

    def recv(self, _n):
        self.calls += 1
        raise self.error


def test_lines_ends_on_a_socket_error_and_keeps_going_on_a_timeout():
    stop = threading.Event()
    assert list(serve._lines(OneChunkThenFail(OSError("reset")), stop)) == []

    class TimeoutThenData:
        def __init__(self):
            self.step = 0

        def settimeout(self, _t):
            pass

        def recv(self, _n):
            self.step += 1
            if self.step == 1:
                raise TimeoutError
            if self.step == 2:
                return b'{"a":1}\n{"b"'
            if self.step == 3:
                return b':2}\n'
            return b""

    assert list(serve._lines(TimeoutThenData(), stop)) == [b'{"a":1}', b'{"b":2}']


def test_lines_stops_when_one_line_grows_beyond_the_limit():
    class Endless:
        def settimeout(self, _t):
            pass

        def recv(self, _n):
            return b"x" * 1024

    assert list(serve._lines(Endless(), threading.Event())) == []


def test_lines_stops_at_once_when_the_stop_event_is_set():
    stop = threading.Event()
    stop.set()
    assert list(serve._lines(OneChunkThenFail(OSError()), stop)) == []


def test_a_bus_failure_ends_the_bus_reader_but_not_the_connection():
    left, right = socket.socketpair()
    seen = threading.Event()

    class FailingGateway:
        to_network = None

        def hello(self):
            return {"type": "hello"}

        def from_bus(self, _can_id, _data):
            seen.set()
            raise OSError("peer gone")

        def from_network(self, message):
            return policy.OK

    bus = LoopbackBus()
    bus.inject(0x111, b"\x01")
    stop = threading.Event()
    worker = threading.Thread(target=serve.serve_connection, args=(left, FailingGateway(), bus, stop), daemon=True)
    worker.start()
    assert seen.wait(5.0)
    right.sendall(b'{"type":"x"}\n')
    right.close()
    worker.join(5.0)
    assert not worker.is_alive()
    left.close()


def test_a_line_that_is_not_json_is_refused_and_logged():
    left, right = socket.socketpair()
    messages: list[str] = []
    received: list[object] = []

    class Gateway:
        to_network = None

        def hello(self):
            return {"type": "hello"}

        def from_bus(self, _can_id, _data):
            return None

        def from_network(self, message):
            received.append(message)
            return policy.Decision(False, "bad_json", "not an object")

    stop = threading.Event()
    worker = threading.Thread(target=serve.serve_connection, args=(left, Gateway(), LoopbackBus(), stop, messages.append), daemon=True)
    worker.start()
    right.sendall(b"{{{\n\xff\xfe\n")
    reader = right.makefile("rb")
    lines = [json.loads(reader.readline()) for _ in range(3)]
    right.close()
    worker.join(5.0)
    assert lines[0]["type"] == "hello" and lines[1] == {"type": "refused", "code": "bad_json"} and lines[2] == lines[1]
    assert received == ["not json", "not json"]
    assert len(messages) == 2 and all("refused bad_json" in m for m in messages)
    left.close()


# ---- the command line --------------------------------------------------------------------------------------------------------------------
def test_running_the_module_as_a_program_prints_the_version(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["urtc-gateway", "--version"])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_module("urtc_gateway.cli", run_name="__main__")
    assert exit_info.value.code == 0
    assert "urtc-gateway" in out.getvalue()


def test_the_command_line_needs_a_command(monkeypatch):
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 2
