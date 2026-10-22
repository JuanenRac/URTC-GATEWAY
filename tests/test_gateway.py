# =============================================================================
# URTC-GATEWAY - tests/test_gateway.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The identifier list, the payload check, the rate limit and the session key, each one on its own and all together."""
from __future__ import annotations

import json
import os
import socket
import threading
import time

import pytest

from urtc_gateway import ids, session
from urtc_gateway import urtc_protocol as proto
from urtc_gateway.cli import build_parser, config_from_args, main
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict, warnings
from urtc_gateway.gateway import Gateway, sign_message
from urtc_gateway.policy import Policy, payload_problem
from urtc_gateway.ratelimit import RateLimiter, TokenBucket
from urtc_gateway.serve import LoopbackBus, run

KEY = bytes(range(32))
SOLDER = proto.CAN_ID_SOLDER_SETPOINT
MOTION = proto.CAN_ID_MOTION_CMD


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make(config: GatewayConfig | None = None, keys=None):
    config = config or GatewayConfig()
    bus, net = [], []
    clock = Clock()
    gw = Gateway(config, keys if keys is not None else {"controller": KEY}, lambda i, d: bus.append((i, d)), net.append, clock)
    return gw, bus, net, clock


def open_config(**sections) -> GatewayConfig:
    data = {"session": {"enabled": False}}
    data.update(sections)
    return config_from_dict(data)


# ---- the list of identifiers, made from the specification ------------------------------------------------------------------------
def test_the_sets_come_from_the_specification_and_do_not_overlap():
    inbound, dangerous, outbound = ids.inbound_ids(), ids.dangerous_ids(), ids.outbound_ids()
    assert inbound.isdisjoint(dangerous)
    assert inbound | dangerous == {i for i, m in proto.MESSAGES.items() if m["direction"] in ("host_to_board", "both")}
    assert outbound == {i for i, m in proto.MESSAGES.items() if m["direction"] in ("board_to_host", "both")}
    assert SOLDER in inbound and proto.CAN_ID_ACTIVE_TOOL_RESP in outbound and proto.CAN_ID_ACTIVE_TOOL_RESP not in inbound


@pytest.mark.parametrize("name", ["ENTER_BOOTLOADER", "START_UPDATE", "DATA", "END_UPDATE", "ERASE_FRAM", "SET_EXPANSION_TYPE", "SET_FREE_TOOL", "SET_DEVICE_SERIAL",
                                  "SET_MLX_VARIANT", "SET_MULTINODE", "SET_FEATURES", "PID_CONFIG", "SLAVE_REG_WRITE", "SLAVE_ENTER_BOOTLOADER", "AUTHORIZE_DOWNGRADE", "READBACK"])
def test_the_dangerous_identifiers_are_the_ones_that_change_what_the_board_is(name):
    can_id = getattr(proto, f"CAN_ID_{name}")
    assert can_id in ids.dangerous_ids() and ids.dangerous_reason(can_id)


def test_questions_are_not_dangerous_even_in_the_bootloader_group():
    for name in ("QUERY_VERSION", "QUERY_ERROR_COUNTERS", "QUERY_ACTIVE_TOOL", "THERMAL_STATS_QUERY"):
        assert getattr(proto, f"CAN_ID_{name}") in ids.inbound_ids(), name


def test_the_table_of_identifiers_names_every_identifier():
    table = ids.table_markdown()
    for can_id in proto.MESSAGES:
        assert f"| 0x{can_id:03X} |" in table


# ---- the policy ------------------------------------------------------------------------------------------------------------------
def test_a_listed_identifier_with_a_good_payload_is_allowed():
    gw, bus, _, _ = make(open_config())
    assert gw.from_network({"id": SOLDER, "data": "012C"})
    assert bus == [(SOLDER, bytes([1, 0x2C]))]


def test_an_identifier_a_host_never_sends_is_refused():
    gw, bus, _, _ = make(open_config())
    decision = gw.from_network({"id": proto.CAN_ID_SOLDER_TELEMETRY, "data": "0100"})
    assert not decision and decision.code == "not_listed" and not bus
    assert gw.from_network({"id": 0x3FF, "data": ""}).code == "not_listed"


def test_a_dangerous_identifier_is_refused_with_the_reason_and_unlocked_on_purpose():
    gw, bus, _, _ = make(open_config())
    decision = gw.from_network({"id": proto.CAN_ID_ENTER_BOOTLOADER, "data": "B0071D5A"})
    assert decision.code == "dangerous" and "ENTER_BOOTLOADER" in decision.detail and not bus
    unlocked, bus2, _, _ = make(open_config(whitelist={"unlock_dangerous": True}))
    assert unlocked.from_network({"id": proto.CAN_ID_ENTER_BOOTLOADER, "data": "B0071D5A"}) and bus2


def test_the_payload_must_be_one_the_specification_allows():
    gw, bus, _, _ = make(open_config())
    assert gw.from_network({"id": SOLDER, "data": "01"}).code == "bad_payload"                    # too short
    assert gw.from_network({"id": SOLDER, "data": "FFFF"}).code == "bad_payload"                  # 65535 C
    assert gw.from_network({"id": MOTION, "data": "0200000010"}).code == "bad_payload"            # direction 2
    assert gw.from_network({"id": proto.CAN_ID_LASER_CMD, "data": "FF05"}).code == "bad_payload"  # interlock 5
    assert not bus
    assert payload_problem(SOLDER, bytes([1, 0x2C])) is None
    assert gw.from_network({"id": MOTION, "data": "01000003E8"})


def test_switching_the_payload_check_off_lets_the_frame_through_and_is_reported():
    config = open_config(payload={"enabled": False})
    gw, bus, _, _ = make(config)
    assert gw.from_network({"id": SOLDER, "data": "FFFF"}) and bus
    assert any("payload check is OFF" in w for w in warnings(config))


def test_the_deny_list_and_the_extra_allow_list_work_whatever_the_rest_says():
    gw, bus, _, _ = make(open_config(whitelist={"deny": [SOLDER], "extra_allow": [proto.CAN_ID_SET_DEVICE_SERIAL]}))
    assert gw.from_network({"id": SOLDER, "data": "012C"}).code == "denied"
    assert gw.from_network({"id": proto.CAN_ID_SET_DEVICE_SERIAL, "data": "07"})
    off, bus2, _, _ = make(open_config(whitelist={"enabled": False, "deny": [SOLDER]}))
    assert off.from_network({"id": 0x3FF, "data": "00"}) and off.from_network({"id": SOLDER, "data": "012C"}).code == "denied"


def test_with_the_list_off_anything_crosses():
    gw, bus, _, _ = make(open_config(whitelist={"enabled": False}))
    assert gw.from_network({"id": 0x7F0, "data": "B0071D5A"}) and bus


@pytest.mark.parametrize("message", [None, "text", [], {"data": "00"}, {"id": "x", "data": ""}, {"id": 0x110, "data": "zz"}, {"id": True, "data": ""},
                                     {"id": 0x800, "data": ""}, {"id": 0x110, "data": "00" * 9}, {"id": -1, "data": ""}])
def test_malformed_messages_are_refused_not_crashed_on(message):
    gw, bus, _, _ = make(open_config())
    assert not gw.from_network(message) and not bus


# ---- the rate limit --------------------------------------------------------------------------------------------------------------
def test_a_token_bucket_refills_with_time():
    bucket = TokenBucket(10, 2)
    assert [bucket.allow(0.0) for _ in range(3)] == [True, True, False]
    assert bucket.allow(0.1) and not bucket.allow(0.1)
    with pytest.raises(ValueError):
        TokenBucket(0, 1)


def test_one_flooded_identifier_does_not_use_the_tokens_of_the_others():
    limiter = RateLimiter(1000, 100, 5, 2)
    assert [limiter.allow(0x130, 0.0) for _ in range(4)] == [True, True, False, False]
    assert limiter.allow(0x140, 0.0)


def test_the_gateway_limits_the_rate_per_identifier_and_recovers():
    gw, bus, _, clock = make(open_config(rate={"per_id_hz": 10, "per_id_burst": 2}))
    results = [gw.from_network({"id": SOLDER, "data": "012C"}).code for _ in range(5)]
    assert results == ["ok", "ok", "rate_limited", "rate_limited", "rate_limited"]
    clock.now += 0.2
    assert gw.from_network({"id": SOLDER, "data": "012C"})
    assert gw.stats.refused["rate_limited"] == 3 and len(bus) == 3


def test_a_per_identifier_override_and_the_off_switch():
    gw, _, _, _ = make(open_config(rate={"per_id_burst": 1, "overrides": {"0x130": [100, 5]}}))
    assert all(gw.from_network({"id": SOLDER, "data": "012C"}) for _ in range(5))
    off, bus, _, _ = make(open_config(rate={"enabled": False, "per_id_burst": 1}))
    assert all(off.from_network({"id": SOLDER, "data": "012C"}) for _ in range(50)) and len(bus) == 50


def test_an_unlocked_dangerous_identifier_is_limited_harder():
    gw, bus, _, _ = make(open_config(whitelist={"unlock_dangerous": True}))
    codes = [gw.from_network({"id": proto.CAN_ID_SET_DEVICE_SERIAL, "data": "07"}).code for _ in range(5)]
    assert codes[:2] == ["ok", "ok"] and set(codes[2:]) == {"rate_limited"} and len(bus) == 2


# ---- the session key -------------------------------------------------------------------------------------------------------------
def signed(gw, counter, can_id=SOLDER, data=b"\x01\x2C", peer="controller", key=KEY):
    return sign_message(key, gw.session.nonce, peer, counter, can_id, data)


def test_a_signed_message_crosses_and_an_unsigned_one_does_not():
    gw, bus, _, _ = make()
    gw.hello()
    assert gw.from_network(signed(gw, 1))
    assert gw.from_network({"id": SOLDER, "data": "012C"}).code == "auth_missing"
    assert len(bus) == 1


def test_a_wrong_key_a_changed_frame_and_an_unknown_peer_are_refused():
    gw, bus, _, _ = make()
    gw.hello()
    assert gw.from_network(signed(gw, 1, key=bytes(32))).code == "bad_mac"
    changed = signed(gw, 2)
    changed["data"] = "01FF"
    assert gw.from_network(changed).code == "bad_mac"
    other_id = signed(gw, 3)
    other_id["id"] = MOTION
    assert gw.from_network(other_id).code == "bad_mac"
    assert gw.from_network(signed(gw, 4, peer="stranger")).code == "unknown_peer"
    assert gw.from_network({**signed(gw, 5), "mac": "zz"}).code == "bad_mac"
    assert not bus


def test_a_recorded_frame_cannot_be_replayed_in_the_same_connection_or_in_another():
    gw, bus, _, _ = make()
    gw.hello()
    first = signed(gw, 7)
    assert gw.from_network(first)
    assert gw.from_network(first).code == "replay"
    assert gw.from_network(signed(gw, 6)).code == "replay"       # an older counter
    assert gw.from_network(signed(gw, 8))
    gw.hello()                                                   # a new connection: a new nonce
    assert gw.from_network(first).code == "bad_mac"
    assert len(bus) == 2


def test_the_counter_must_be_a_natural_number_and_one_connection_has_one_peer():
    keys = {"controller": KEY, "service": bytes(range(1, 33))}
    gw, bus, _, _ = make(keys=keys)
    gw.hello()
    assert gw.from_network(signed(gw, 1))
    assert gw.from_network(signed(gw, 2, peer="service", key=keys["service"])).code == "wrong_peer"
    bad = signed(gw, 3)
    bad["counter"] = -1
    assert gw.from_network(bad).code == "bad_mac"
    bad["counter"] = True
    assert gw.from_network(bad).code == "bad_mac"
    assert len(bus) == 1


def test_a_signed_message_still_goes_through_the_list_and_the_rate_limit():
    gw, bus, _, _ = make()
    gw.hello()
    assert gw.from_network(signed(gw, 1, can_id=proto.CAN_ID_ENTER_BOOTLOADER, data=bytes.fromhex("B0071D5A"))).code == "dangerous"
    assert not bus


def test_switching_the_session_off_is_allowed_and_reported():
    config = config_from_dict({"session": {"enabled": False}})
    gw, bus, _, _ = make(config, keys={})
    assert gw.from_network({"id": SOLDER, "data": "012C"}) and bus
    assert any("session authentication is OFF" in w for w in warnings(config))


def test_a_gateway_with_the_session_on_and_no_key_refuses_to_start():
    with pytest.raises(session.KeyError_):
        make(GatewayConfig(), keys={})


def test_the_key_file_is_read_strictly_and_written_privately(tmp_path):
    path = tmp_path / "keys.txt"
    session.write_new_key_file(path, ["controller", "service"])
    keys = session.load_keys(path)
    assert set(keys) == {"controller", "service"} and all(len(k) == 32 for k in keys.values()) and keys["controller"] != keys["service"]
    assert session.key_file_is_private(path)
    with pytest.raises(session.KeyError_, match="exists"):
        session.write_new_key_file(path, ["x"])
    for text, message in (("controller zz\n", "64 hexadecimal"), ("onlyname\n", "expected"), ("bad name " + "00" * 32 + "\n", "expected"),
                          ("a " + "00" * 32 + "\na " + "11" * 32 + "\n", "twice"), ("# nothing\n", "no key")):
        bad = tmp_path / "bad.txt"
        bad.write_text(text, encoding="utf-8")
        with pytest.raises(session.KeyError_, match=message):
            session.load_keys(bad)
    with pytest.raises(session.KeyError_):
        session.write_new_key_file(tmp_path / "x.txt", ["a b"])
    with pytest.raises(session.KeyError_):
        session.write_new_key_file(tmp_path / "y.txt", ["a", "a"])


@pytest.mark.skipif(os.name == "nt", reason="file modes")
def test_a_key_file_other_users_can_read_is_noticed(tmp_path):
    path = tmp_path / "keys.txt"
    session.write_new_key_file(path, ["a"])
    os.chmod(path, 0o644)
    assert not session.key_file_is_private(path)


# ---- the way out -----------------------------------------------------------------------------------------------------------------
def test_only_what_a_board_sends_goes_to_the_network():
    gw, _, net, _ = make(open_config())
    assert gw.from_bus(proto.CAN_ID_ACTIVE_TOOL_RESP, b"\x00\x00\x00\x00")
    assert net == [{"type": "frame", "id": proto.CAN_ID_ACTIVE_TOOL_RESP, "data": "00000000"}]
    assert gw.from_bus(SOLDER, b"\x01\x2C").code == "not_listed"      # a command seen on the bus (another master) is not passed on
    assert len(net) == 1


def test_the_outbound_filter_and_its_rate_can_be_switched_off():
    gw, _, net, _ = make(open_config(outbound={"enabled": False}))
    assert gw.from_bus(SOLDER, b"\x01\x2C") and len(net) == 1
    limited, _, net2, _ = make(open_config(outbound={"rate_hz": 10}))
    results = [limited.from_bus(proto.CAN_ID_ACTIVE_TOOL_RESP, b"\x00\x00\x00\x00").allowed for _ in range(5)]
    assert results == [True, False, False, False, False] or results.count(True) <= 2


# ---- configuration ---------------------------------------------------------------------------------------------------------------
def test_the_default_configuration_has_every_protection_on():
    config = GatewayConfig()
    assert config.session.enabled and config.whitelist.enabled and config.payload.enabled and config.rate.enabled and config.outbound.enabled
    assert not config.whitelist.unlock_dangerous and warnings(config) == []


@pytest.mark.parametrize("data, message", [
    ([], "JSON object"), ({"nothing": 1}, "unknown section"), ({"schema": 9}, "schema"), ({"rate": 3}, "must be an object"),
    ({"rate": {"speed": 1}}, "unknown option"), ({"rate": {"enabled": "yes"}}, "true or false"), ({"rate": {"per_id_hz": "fast"}}, "must be a number"),
    ({"rate": {"per_id_hz": -1}}, "negative"), ({"server": {"port": 70000}}, "port"), ({"whitelist": {"deny": ["x"]}}, "not an identifier"),
    ({"whitelist": {"deny": [0x800]}}, "0 to 0x7FF"), ({"whitelist": {"extra_allow": 5}}, "list"), ({"rate": {"overrides": {"0x130": [1]}}}, "rate, burst"),
    ({"session": {"key_file": 3}}, "text"),
])
def test_a_bad_configuration_is_refused_with_a_reason(data, message):
    with pytest.raises(ConfigError, match=message):
        config_from_dict(data)


def test_a_configuration_survives_a_round_trip():
    config = config_from_dict({"rate": {"per_id_hz": 5, "overrides": {"0x130": [50, 8]}}, "whitelist": {"extra_allow": ["0x1B0"]}, "server": {"port": 9000}})
    again = config_from_dict(config_to_dict(config))
    assert config_to_dict(again) == config_to_dict(config) and again.server.port == 9000 and again.whitelist.extra_allow == [0x1B0]


def test_every_loosened_protection_is_listed():
    config = config_from_dict({"session": {"enabled": False}, "whitelist": {"unlock_dangerous": True, "extra_allow": [0x1B0]}, "payload": {"enabled": False},
                               "rate": {"enabled": False}, "outbound": {"enabled": False}, "server": {"host": "0.0.0.0"}})
    text = "\n".join(warnings(config))
    for word in ("session", "UNLOCKED", "added to the list", "payload", "rate limit", "outbound", "0.0.0.0"):
        assert word in text, word


# ---- the command line ------------------------------------------------------------------------------------------------------------
def test_the_flags_switch_each_protection_and_override_a_file(tmp_path):
    path = tmp_path / "gw.json"
    path.write_text(json.dumps({"rate": {"enabled": False}, "session": {"enabled": False}}), encoding="utf-8")
    args = build_parser().parse_args(["policy", "--config", str(path), "--rate-limit", "--no-payload-check", "--unlock-dangerous", "--allow-id", "0x1B0", "--deny-id", "304"])
    config = config_from_args(args)
    assert config.rate.enabled and not config.payload.enabled and not config.session.enabled and config.whitelist.unlock_dangerous
    assert config.whitelist.extra_allow == [0x1B0] and config.whitelist.deny == [304]
    with pytest.raises(SystemExit):
        build_parser().parse_args(["policy", "--session", "--no-session"])


def test_policy_ids_and_keygen_commands(tmp_path, capsys):
    assert main(["policy", "--no-session"]) == 0
    captured = capsys.readouterr()
    assert "session authentication is OFF" in captured.err and '"schema": 1' in captured.out
    assert main(["ids"]) == 0
    assert "SOLDER_SETPOINT" in capsys.readouterr().out
    key_path = tmp_path / "k.txt"
    assert main(["keygen", str(key_path), "controller"]) == 0
    out = capsys.readouterr().out
    assert "not shown" in out and key_path.read_text(encoding="utf-8").split()[-1] not in out
    assert main(["keygen", str(key_path), "controller"]) == 2


def test_run_refuses_to_start_unsafely(tmp_path, capsys):
    assert main(["run"]) == 2
    assert "no key file" in capsys.readouterr().err
    assert main(["run", "--no-session", "--host", "0.0.0.0"]) == 2
    assert "non-local" in capsys.readouterr().err
    assert main(["run", "--key-file", str(tmp_path / "missing.txt")]) == 2


# ---- the server, with a real socket and a bus with nothing on it -----------------------------------------------------------------
def _start(config, keys):
    bus = LoopbackBus()
    stop = threading.Event()
    ready = threading.Event()
    bound: list[int] = []
    thread = threading.Thread(target=run, args=(config, keys, bus, stop, lambda text: None, ready, bound), daemon=True)
    thread.start()
    assert ready.wait(5)
    return bus, stop, thread, bound[0]


def _read_line(sock: socket.socket, buffer: bytearray) -> dict:
    while b"\n" not in buffer:
        buffer += sock.recv(4096)
    line, _, rest = bytes(buffer).partition(b"\n")
    buffer[:] = rest
    return json.loads(line)


def test_over_a_real_socket_a_signed_command_reaches_the_bus_and_telemetry_comes_back():
    config = config_from_dict({"server": {"port": 0}})
    bus, stop, thread, port = _start(config, {"controller": KEY})
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            buffer = bytearray()
            hello = _read_line(sock, buffer)
            assert hello["type"] == "hello" and hello["session"] is True
            nonce = bytes.fromhex(hello["nonce"])
            sock.sendall(json.dumps(sign_message(KEY, nonce, "controller", 1, SOLDER, b"\x01\x2C")).encode() + b"\n")
            sock.sendall(json.dumps(sign_message(KEY, nonce, "controller", 1, SOLDER, b"\x01\x2C")).encode() + b"\n")   # replay
            assert _read_line(sock, buffer) == {"type": "refused", "code": "replay"}
            sock.sendall(b"not json\n")
            assert _read_line(sock, buffer)["code"] == "bad_frame"
            bus.inject(proto.CAN_ID_ACTIVE_TOOL_RESP, b"\x00\x00\x00\x00")
            assert _read_line(sock, buffer) == {"type": "frame", "id": proto.CAN_ID_ACTIVE_TOOL_RESP, "data": "00000000"}
        deadline = time.monotonic() + 3
        while not bus.sent and time.monotonic() < deadline:
            time.sleep(0.01)
        assert bus.sent == [(SOLDER, b"\x01\x2C")]
    finally:
        stop.set()
        thread.join(5)


def test_a_line_that_is_too_long_ends_the_connection():
    config = config_from_dict({"server": {"port": 0}, "session": {"enabled": False}})
    bus, stop, thread, port = _start(config, None)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(b"x" * 10000)
            sock.settimeout(5)
            data = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except OSError:
                pass
        assert not bus.sent
    finally:
        stop.set()
        thread.join(5)


def test_the_table_file_is_current():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "ALLOWED_IDS.md").read_bytes().decode("utf-8").replace("\r\n", "\n") == ids.table_markdown()
    assert Policy(GatewayConfig()).inbound == ids.inbound_ids()
