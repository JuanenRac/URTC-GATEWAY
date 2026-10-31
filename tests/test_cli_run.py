# =============================================================================
# URTC-GATEWAY - tests/test_cli_run.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The `run` command: what it refuses before it listens, what it warns about, and that the bus is always closed. The server itself is replaced by a stand-in."""
from __future__ import annotations

import argparse

import pytest

from urtc_gateway import cli, serve


class FakeBus:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def fake_server(monkeypatch):
    calls: list[tuple] = []
    bus = FakeBus()
    monkeypatch.setattr(serve, "LoopbackBus", lambda: bus)
    monkeypatch.setattr(serve, "run", lambda config, keys, the_bus, stop: calls.append((config, keys, the_bus, stop)))
    return calls, bus


def test_an_identifier_is_parsed_in_any_base_and_a_bad_one_is_refused():
    assert cli._id("0x120") == 0x120
    assert cli._id("288") == 288
    with pytest.raises(argparse.ArgumentTypeError, match="is not an identifier"):
        cli._id("MOTION")
    with pytest.raises(argparse.ArgumentTypeError, match="0 to 0x7FF"):
        cli._id("0x800")
    with pytest.raises(argparse.ArgumentTypeError):
        cli._id("-1")


def test_the_flags_change_the_configuration_over_the_defaults():
    args = cli.build_parser().parse_args(["run", "--no-session", "--no-rate-limit", "--unlock-dangerous", "--allow-id", "0x130", "--deny-id", "0x120",
                                          "--host", "127.0.0.1", "--port", "9000", "--allow-open-network", "--key-file", "keys.txt"])
    config = cli.config_from_args(args)
    assert config.session.enabled is False and config.rate.enabled is False
    assert config.whitelist.unlock_dangerous is True
    assert 0x130 in config.whitelist.extra_allow and 0x120 in config.whitelist.deny
    assert config.server.port == 9000 and config.server.allow_open_network is True
    assert config.session.key_file == "keys.txt"


def test_a_protection_cannot_be_switched_off_and_on_at_once():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["policy", "--no-session", "--session"])


def test_running_with_session_authentication_needs_a_key_file(capsys, fake_server):
    calls, _bus = fake_server
    assert cli.main(["run"]) == 2
    assert "no key file was given" in capsys.readouterr().err
    assert calls == []


def test_a_missing_key_file_is_reported_not_raised(capsys, fake_server, tmp_path):
    calls, _bus = fake_server
    assert cli.main(["run", "--key-file", str(tmp_path / "nothing.keys")]) == 2
    assert capsys.readouterr().err.startswith("error:")
    assert calls == []


def test_a_non_local_address_without_session_authentication_is_refused(capsys, fake_server):
    calls, _bus = fake_server
    assert cli.main(["run", "--no-session", "--host", "0.0.0.0"]) == 2
    assert "refusing to listen on a non-local address" in capsys.readouterr().err
    assert calls == []


def test_a_non_local_address_can_be_allowed_on_purpose_and_the_bus_is_closed(capsys, fake_server):
    calls, bus = fake_server
    assert cli.main(["run", "--no-session", "--host", "0.0.0.0", "--allow-open-network"]) == 0
    assert len(calls) == 1 and calls[0][1] is None and calls[0][2] is bus
    assert bus.closed is True
    assert "WARNING" in capsys.readouterr().err   # the protections that are off are said


def test_a_key_file_that_other_users_can_read_is_warned_about(capsys, fake_server, tmp_path, monkeypatch):
    calls, bus = fake_server
    key_file = tmp_path / "gateway.keys"
    from urtc_gateway import session

    session.write_new_key_file(str(key_file), ["panel"])
    monkeypatch.setattr(session, "key_file_is_private", lambda path: False)
    assert cli.main(["run", "--key-file", str(key_file)]) == 0
    assert "can be read by other users" in capsys.readouterr().err
    assert calls and calls[0][1] is not None and bus.closed is True


def test_stopping_with_the_keyboard_sets_the_event_and_closes_the_bus(fake_server, monkeypatch):
    _calls, bus = fake_server
    seen = {}

    def interrupted(config, keys, the_bus, stop):
        seen["stop"] = stop
        raise KeyboardInterrupt

    monkeypatch.setattr(serve, "run", interrupted)
    assert cli.main(["run", "--no-session"]) == 0
    assert seen["stop"].is_set() is True and bus.closed is True


def test_a_serial_bus_that_cannot_be_opened_is_reported(capsys, monkeypatch):
    def refuse(port, bitrate):
        raise RuntimeError(f"cannot open {port}")

    monkeypatch.setattr(serve, "SerialSlcanBus", refuse)
    assert cli.main(["run", "--no-session", "--bus", "COM99"]) == 2
    assert "cannot open COM99" in capsys.readouterr().err


def test_a_configuration_file_that_is_wrong_is_reported_with_exit_code_2(capsys, tmp_path):
    broken = tmp_path / "gateway.json"
    broken.write_text("{not json", encoding="utf-8")
    assert cli.main(["policy", "--config", str(broken)]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_keygen_never_overwrites_and_reports_the_error(capsys, tmp_path):
    target = tmp_path / "gateway.keys"
    assert cli.main(["keygen", str(target), "a", "b"]) == 0
    out = capsys.readouterr().out
    assert "2 key(s)" in out and "the keys are not shown" in out
    assert cli.main(["keygen", str(target), "a"]) == 2
    assert capsys.readouterr().err.startswith("error:")
