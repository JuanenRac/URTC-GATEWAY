# =============================================================================
# URTC-GATEWAY - tests/test_actuator_peers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The commands that move, heat or switch an output can be limited to named peers; by default every peer may send them."""
from __future__ import annotations

import pytest

from urtc_gateway import ids
from urtc_gateway.cli import build_parser, config_from_args
from urtc_gateway.config import ConfigError, GatewayConfig, config_from_dict, config_to_dict, warnings
from urtc_gateway.gateway import Gateway, sign_message

KEYS = {"controller": bytes(range(32)), "viewer": bytes(range(1, 33))}
LASER = 0x160
GLOBAL_STATUS = 0x100


def _gateway(**whitelist):
    config = config_from_dict({"whitelist": whitelist, "payload": {"enabled": False}})
    bus: list = []
    gw = Gateway(config, KEYS, lambda i, d: bus.append((i, d)), lambda _m: None, lambda: 0.0)
    return gw, bus


def _send(gw: Gateway, peer: str, can_id: int, counter: int = 1):
    nonce = bytes.fromhex(gw.hello()["nonce"])
    return gw.from_network(sign_message(KEYS[peer], nonce, peer, counter, can_id, b"\x00\x00"))


def test_the_actuator_set_comes_from_the_groups_of_the_specification():
    actuators = ids.actuator_ids()
    assert {0x120, 0x130, 0x140, LASER, 0x170, 0x1B0, 0x1C0, 0x1E0, 0x1F0, 0x200} <= actuators
    assert not {GLOBAL_STATUS, 0x110, 0x190, 0x1A8, 0x250, 0x7F8} & actuators
    assert actuators & ids.dangerous_ids() == {0x131}   # the reset of the solder feeder moves it: unlocking it is not enough without the actuator permission


def test_by_default_every_peer_may_send_an_actuator_command():
    assert GatewayConfig().whitelist.allow_actuators is True
    gw, bus = _gateway()
    assert _send(gw, "viewer", LASER)
    assert [i for i, _ in bus] == [LASER]


def test_switched_off_only_the_named_peer_gets_through():
    gw, bus = _gateway(allow_actuators=False, actuator_peers=["controller"])
    refused = _send(gw, "viewer", LASER)
    assert not refused and refused.code == "actuator" and bus == []
    assert _send(gw, "viewer", GLOBAL_STATUS)
    assert _send(gw, "controller", LASER)
    assert [i for i, _ in bus] == [GLOBAL_STATUS, LASER]


def test_switched_off_with_no_names_nobody_gets_through():
    gw, bus = _gateway(allow_actuators=False)
    assert _send(gw, "controller", LASER).code == "actuator" and bus == []


def test_without_a_session_a_claimed_name_is_not_trusted():
    config = config_from_dict({"session": {"enabled": False}, "whitelist": {"allow_actuators": False, "actuator_peers": ["controller"]}})
    bus: list = []
    gw = Gateway(config, {}, lambda i, d: bus.append((i, d)), lambda _m: None, lambda: 0.0)
    assert gw.from_network({"id": LASER, "data": "0000", "peer": "controller"}).code == "actuator"
    assert bus == []
    assert any("lets nobody send" in w for w in warnings(config))


def test_the_start_lists_who_is_allowed_and_a_list_with_no_effect():
    allowed = config_from_dict({"whitelist": {"allow_actuators": False, "actuator_peers": ["controller"]}})
    assert "peers allowed to send actuator commands: controller" in warnings(allowed)
    idle = config_from_dict({"whitelist": {"actuator_peers": ["controller"]}})
    assert any("has no effect" in w for w in warnings(idle))
    assert not any("actuator" in w for w in warnings(GatewayConfig()))


def test_the_options_come_from_the_file_and_the_command_line():
    args = build_parser().parse_args(["policy", "--no-actuators", "--actuator-peer", "controller"])
    config = config_from_args(args)
    assert config.whitelist.allow_actuators is False and config.whitelist.actuator_peers == ["controller"]
    assert config_from_dict(config_to_dict(config)) == config


@pytest.mark.parametrize("bad", [{"allow_actuators": 1}, {"actuator_peers": "controller"}, {"actuator_peers": [""]}, {"actuator_peers": [3]}])
def test_a_wrong_value_is_an_error(bad):
    with pytest.raises(ConfigError):
        config_from_dict({"whitelist": bad})
